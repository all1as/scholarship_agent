"""Тетрадь: состояние системы между запросами (design doc, раздел 6; ADR-001, ADR-002).

Типы состояния и где живут:
- L0 `l0_pages`      — кэш/сырьё: снимки страниц (текст, sha256, дата загрузки). Неизменяемы; новая загрузка = новая строка.
- L1 `l1_facts`      — фактическая память: атомарный факт + источник + цитата + дата проверки + статус жизни.
                        Факты не удаляются и не перезаписываются: retract / quarantine / supersede с записью в журнал.
- L1 `l1_events`     — журнал изменений фактов (след разрешения противоречий и чисток).
- L2 `l2_cards`      — производное: карточка стипендии, всегда пересчитывается из активных фактов L1.
- `sessions`         — эпизодическая память: реплики диалога и свёрнутое резюме старых реплик (в пределах сессии).
- `user_lists`       — состояние пользователя, переживающее границу сессии: избранное.
- `extract_cache`    — кэш извлечения: (sha256 страницы, хэш промпта) → JSON; страница не изменилась → модель не вызывается.
Рабочее состояние задачи (шаги, бюджет, частичный результат) живёт в harness.core.Context и после задачи не хранится.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date, datetime

from .rules import TARGET_CYCLE, cycle_status, deadline_outcome, resolve_date

SOURCE_RANK = {"official": 3, "university": 3, "user": 2, "aggregator": 1, "past_snapshot": 0}
FRESH_DAYS = 14             # факт старше — «устарел» до перепроверки
FRESH_URGENT_HOURS = 72     # для дедлайнов ближе 30 дней
URGENT_DAYS = 30

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS l0_pages (
  page TEXT, scholarship_id TEXT, url TEXT, sha256 TEXT, fetched_at TEXT, source TEXT, text TEXT,
  PRIMARY KEY (page, sha256));
CREATE TABLE IF NOT EXISTS l1_facts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, scholarship_id TEXT, field TEXT, value TEXT, cycle TEXT,
  scope TEXT, scope_detail TEXT, quote TEXT, page TEXT, source_url TEXT, source_type TEXT,
  checked_at TEXT, status TEXT DEFAULT 'active', fingerprint TEXT UNIQUE, note TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS l1_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, fact_id INTEGER, action TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS l2_cards (scholarship_id TEXT PRIMARY KEY, card TEXT, computed_at TEXT);
CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT, turn INTEGER, role TEXT, text TEXT, ts TEXT, PRIMARY KEY (session_id, turn));
CREATE TABLE IF NOT EXISTS session_summary (session_id TEXT PRIMARY KEY, summary TEXT, upto_turn INTEGER);
CREATE TABLE IF NOT EXISTS user_lists (user_id TEXT, scholarship_id TEXT, added_at TEXT, PRIMARY KEY (user_id, scholarship_id));
CREATE TABLE IF NOT EXISTS extract_cache (page_sha TEXT, prompt_sha TEXT, data TEXT, PRIMARY KEY (page_sha, prompt_sha));
"""


class NotebookError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}")
        self.code = code


class Notebook:
    def __init__(self, path: str = ":memory:", clock: str = "2026-10-25"):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA_SQL)
        self.clock = clock          # «сегодня»; в eval — дата заморозки, чтобы прогон был воспроизводим

    # ---------- L0 ----------
    def put_page(self, page: str, url: str, text: str, fetched_at: str, source: str) -> tuple[str, bool]:
        """Возвращает (sha256, изменилась ли страница относительно последнего снимка)."""
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        last = self.db.execute("SELECT sha256 FROM l0_pages WHERE page=? ORDER BY fetched_at DESC LIMIT 1",
                               (page,)).fetchone()
        self.db.execute("INSERT OR IGNORE INTO l0_pages VALUES (?,?,?,?,?,?,?)",
                        (page, page.split("/")[0], url, sha, fetched_at, source, text))
        return sha, (last is None or last["sha256"] != sha)

    def page_text(self, page: str) -> str | None:
        r = self.db.execute("SELECT text FROM l0_pages WHERE page=? ORDER BY fetched_at DESC LIMIT 1", (page,)).fetchone()
        return r["text"] if r else None

    def last_fetch(self, page: str) -> str | None:
        r = self.db.execute("SELECT fetched_at FROM l0_pages WHERE page=? ORDER BY fetched_at DESC LIMIT 1", (page,)).fetchone()
        return r["fetched_at"] if r else None

    # ---------- кэш извлечения ----------
    def cached_extract(self, page_sha: str, prompt_sha: str) -> dict | None:
        r = self.db.execute("SELECT data FROM extract_cache WHERE page_sha=? AND prompt_sha=?", (page_sha, prompt_sha)).fetchone()
        return json.loads(r["data"]) if r else None

    def cache_extract(self, page_sha: str, prompt_sha: str, data: dict) -> None:
        self.db.execute("INSERT OR REPLACE INTO extract_cache VALUES (?,?,?)", (page_sha, prompt_sha, json.dumps(data)))

    # ---------- L1 ----------
    def _event(self, fact_id: int | None, action: str, reason: str) -> None:
        self.db.execute("INSERT INTO l1_events (ts, fact_id, action, reason) VALUES (?,?,?,?)",
                        (self.clock, fact_id, action, reason))

    def add_fact(self, sid: str, field: str, value, *, source_type: str, quote: str | None, page: str | None,
                 source_url: str | None, checked_at: str, cycle: str | None = None, scope: str = "global",
                 scope_detail: str | None = None, note: str = "") -> tuple[int, bool]:
        """Идемпотентно: тот же факт из того же источника второй раз не пишется. Возвращает (id, создан ли)."""
        v = json.dumps(value, sort_keys=True, ensure_ascii=False)
        fp = hashlib.sha256("|".join(map(str, (sid, field, v, cycle, scope, source_type, source_url, quote))).encode()).hexdigest()[:24]
        row = self.db.execute("SELECT id, status FROM l1_facts WHERE fingerprint=?", (fp,)).fetchone()
        if row:
            if row["status"] == "active":
                self.db.execute("UPDATE l1_facts SET checked_at=? WHERE id=?", (max(checked_at, self._checked(row["id"])), row["id"]))
            self._event(row["id"], "duplicate_ignored", f"повтор записи ({row['status']})")
            return row["id"], False
        cur = self.db.execute(
            "INSERT INTO l1_facts (scholarship_id, field, value, cycle, scope, scope_detail, quote, page, source_url,"
            " source_type, checked_at, fingerprint, note, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (sid, field, v, cycle, scope, scope_detail, quote, page, source_url, source_type, checked_at, fp, note, self.clock))
        self._event(cur.lastrowid, "insert", f"{source_type}: {note}".strip(": "))
        return cur.lastrowid, True

    def _checked(self, fact_id: int) -> str:
        return self.db.execute("SELECT checked_at FROM l1_facts WHERE id=?", (fact_id,)).fetchone()["checked_at"]

    def set_status(self, fact_id: int, status: str, reason: str) -> None:
        row = self.db.execute("SELECT status FROM l1_facts WHERE id=?", (fact_id,)).fetchone()
        if row is None:
            raise NotebookError("not_found", f"факт {fact_id}")
        if row["status"] == status:
            raise NotebookError(f"already_{status}", f"факт {fact_id}")
        if row["status"] != "active" and status != "active":
            raise NotebookError("not_active", f"факт {fact_id} в статусе {row['status']}")
        self.db.execute("UPDATE l1_facts SET status=? WHERE id=?", (status, fact_id))
        self._event(fact_id, status, reason)

    def facts(self, sid: str, field: str | None = None, active_only: bool = True) -> list[dict]:
        q = "SELECT * FROM l1_facts WHERE scholarship_id=?" + (" AND status='active'" if active_only else "")
        args: list = [sid]
        if field:
            q += " AND field=?"
            args.append(field)
        out = []
        for r in self.db.execute(q + " ORDER BY id", args):
            d = dict(r)
            d["value"] = json.loads(d["value"])
            out.append(d)
        return out

    def events(self, fact_id: int | None = None) -> list[dict]:
        q, args = "SELECT * FROM l1_events", ()
        if fact_id is not None:
            q, args = q + " WHERE fact_id=?", (fact_id,)
        return [dict(r) for r in self.db.execute(q + " ORDER BY id", args)]

    # ---------- исправления пользователя (запись во «внешнее» состояние: повтор и отмена) ----------
    def user_correction(self, sid: str, field: str, value, *, user: str, cycle: str | None = None,
                        scope: str = "global", note: str = "") -> tuple[int, bool]:
        # пользователь говорит о текущем цикле, если не сказал иного — иначе исправление «проиграло» бы молча
        cycle = cycle or (TARGET_CYCLE if field == "application_deadline" else None)
        fid, created = self.add_fact(sid, field, value, source_type="user", quote=None, page=None,
                                     source_url=f"user:{user}", checked_at=self.clock, cycle=cycle, scope=scope,
                                     note=note or "исправление пользователя")
        self.recompute(sid)
        return fid, created

    def undo_correction(self, fact_id: int, reason: str = "отмена пользователем") -> None:
        row = self.db.execute("SELECT scholarship_id, source_type FROM l1_facts WHERE id=?", (fact_id,)).fetchone()
        if row is None:
            raise NotebookError("not_found", f"исправление {fact_id}")
        if row["source_type"] != "user":
            raise NotebookError("not_a_correction", f"факт {fact_id} не от пользователя")
        self.set_status(fact_id, "retracted", reason)
        self.recompute(row["scholarship_id"])

    # ---------- аудит L1 по L0 (чистка отравления) ----------
    def audit(self, norm) -> list[int]:
        """Каждый активный факт со страницы обязан иметь цитату, буквально присутствующую в снимке L0.
        Факт без подтверждения → quarantine (не удаляется, след в журнале). Возвращает id помещённых в карантин."""
        bad = []
        for r in self.db.execute("SELECT * FROM l1_facts WHERE status='active' AND source_type!='user'").fetchall():
            text = self.page_text(r["page"]) if r["page"] else None
            if not text or not r["quote"] or norm(r["quote"]) not in norm(text):
                self.set_status(r["id"], "quarantined", "цитата не найдена в L0" if text else "нет снимка L0")
                bad.append(r["id"])
        for sid in {r["scholarship_id"] for r in self.db.execute(
                f"SELECT scholarship_id FROM l1_facts WHERE id IN ({','.join('?' * len(bad))})", bad)} if bad else ():
            self.recompute(sid)
        return bad

    # ---------- L2: карточка из L1 по политике противоречий (ADR-002) ----------
    def recompute(self, sid: str) -> dict:
        dls = self.facts(sid, "application_deadline")
        amounts = self.facts(sid, "amount")
        card = {"scholarship_id": sid, "deadline": _resolve_deadlines(dls, self.clock),
                "amount": _resolve_amount(amounts, self.clock), "computed_at": self.clock,
                "l1_active": len(self.facts(sid))}
        self.db.execute("INSERT OR REPLACE INTO l2_cards VALUES (?,?,?)",
                        (sid, json.dumps(card, ensure_ascii=False), self.clock))
        return card

    def card(self, sid: str) -> dict | None:
        r = self.db.execute("SELECT card FROM l2_cards WHERE scholarship_id=?", (sid,)).fetchone()
        return json.loads(r["card"]) if r else None

    def cards(self) -> list[dict]:
        return [json.loads(r["card"]) for r in self.db.execute("SELECT card FROM l2_cards ORDER BY scholarship_id")]

    # ---------- L3: резюме (код, без модели) ----------
    def summary_l3(self, limit: int = 15) -> dict:
        rows = []
        for c in self.cards():
            w = c["deadline"]["working"]
            if w:
                rows.append({"id": c["scholarship_id"], "deadline": w["date"], "status": c["deadline"]["status"]})
        rows.sort(key=lambda x: resolve_date(x["deadline"], TARGET_CYCLE) or "9999")
        attention = [r for r in rows if r["status"] in ("конфликт", "вероятен", "устарел")]
        return {"today": self.clock, "nearest": rows[:limit], "attention": attention[:limit],
                "total_cards": len(self.cards())}

    # ---------- эпизодическая память ----------
    def add_turn(self, session_id: str, role: str, text: str) -> int:
        n = self.db.execute("SELECT COALESCE(MAX(turn),0)+1 FROM sessions WHERE session_id=?", (session_id,)).fetchone()[0]
        self.db.execute("INSERT INTO sessions VALUES (?,?,?,?,?)", (session_id, n, role, text, self.clock))
        return n

    def turns(self, session_id: str) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM sessions WHERE session_id=? ORDER BY turn", (session_id,))]

    def set_summary(self, session_id: str, summary: str, upto_turn: int) -> None:
        self.db.execute("INSERT OR REPLACE INTO session_summary VALUES (?,?,?)", (session_id, summary, upto_turn))

    def summary(self, session_id: str) -> tuple[str, int]:
        r = self.db.execute("SELECT summary, upto_turn FROM session_summary WHERE session_id=?", (session_id,)).fetchone()
        return (r["summary"], r["upto_turn"]) if r else ("", 0)

    # ---------- состояние пользователя между сессиями ----------
    # Граница сессии — новый session_id (в продукте: команда «новый разговор» или 24 ч без реплик).
    # Через границу переходит состояние пользователя: избранное (user_lists), профиль, исправления в L1.
    # Не переходят реплики прошлой сессии и рабочее состояние задач.
    def add_favorite(self, user: str, sid: str) -> bool:
        cur = self.db.execute("INSERT OR IGNORE INTO user_lists VALUES (?,?,?)", (user, sid, self.clock))
        return cur.rowcount == 1

    def remove_favorite(self, user: str, sid: str) -> bool:
        return self.db.execute("DELETE FROM user_lists WHERE user_id=? AND scholarship_id=?", (user, sid)).rowcount == 1

    def favorites(self, user: str) -> list[str]:
        return [r["scholarship_id"] for r in self.db.execute(
            "SELECT scholarship_id FROM user_lists WHERE user_id=? ORDER BY added_at, scholarship_id", (user,))]


# ---------- политика противоречий ----------

def _as_date(s: str) -> date:
    """'YYYY-MM' (точность «месяц») → первое число: для срочности и свежести берём более раннюю границу."""
    s = s[:10]
    return date.fromisoformat(s + "-01" if len(s) == 7 else s)


def _days(a: str, b: str) -> int:
    return (_as_date(b) - _as_date(a)).days


def _fresh(checked_at: str, clock: str, urgent: bool) -> bool:
    if urgent:
        return (datetime.fromisoformat(clock) - datetime.fromisoformat(checked_at[:10])).total_seconds() <= FRESH_URGENT_HOURS * 3600
    return _days(checked_at, clock) <= FRESH_DAYS


def _cycle_rank(c: str | None) -> str:
    return c or "0000"


def _public(f: dict) -> dict:
    return {"value": f["value"], "cycle": f["cycle"], "scope": f["scope"], "scope_detail": f["scope_detail"],
            "source_type": f["source_type"], "source_url": f["source_url"], "quote": f["quote"],
            "checked_at": f["checked_at"], "fact_id": f["id"]}


def _resolve_deadlines(facts: list[dict], clock: str) -> dict:
    """Правила (ADR-002):
    1. retracted/quarantined/superseded не участвуют (но остаются в L1 и журнале);
    2. новый цикл важнее старого;
    3. в одном цикле: официальный/вуз > пользователь > агрегатор > прошлогодний снимок;
    4. исключение: официальный и пользователь расходятся в одном цикле → рабочее значение — более РАННЯЯ дата
       (ошибка «дата позже реальной» критична, ранняя дата безопаснее), статус «конфликт»;
    5. любое расхождение в выбранном цикле → «конфликт», показываются все значения с источниками."""
    if not facts:
        # «не указано» — на страницах дедлайна нет (неизвестно); это не «стипендия не найдена» и не «дедлайна не существует»
        return {"working": None, "status": "не указано", "cycle_status": "not_found", "outcome": "not_stated",
                "alternatives": []}
    as_label = [{"cycle": f["cycle"]} for f in facts if f["source_type"] in ("official", "university", "user")]
    top_cycle = max((_cycle_rank(f["cycle"]) for f in facts))
    same = [f for f in facts if _cycle_rank(f["cycle"]) == top_cycle]
    same.sort(key=lambda f: (SOURCE_RANK[f["source_type"]], f["checked_at"]), reverse=True)
    best = same[0]
    differing = [f for f in same if f["value"] != best["value"] and f["scope"] == best["scope"]]
    status = None
    if differing:
        status = "конфликт"
        user_vs_official = {f["source_type"] for f in same} >= {"user"} and any(
            SOURCE_RANK[f["source_type"]] == 3 for f in same)
        if user_vs_official:
            cands = [f for f in same if f["source_type"] in ("user", "official", "university")]
            best = min(cands, key=lambda f: resolve_date(f["value"], f["cycle"] or TARGET_CYCLE) or "9999")
    others = [f for f in facts if f["id"] != best["id"]]
    resolved = resolve_date(best["value"], best["cycle"] or TARGET_CYCLE)
    urgent = bool(resolved) and 0 <= _days(clock, resolved) <= URGENT_DAYS
    if status is None:
        if best["cycle"] and best["cycle"] < TARGET_CYCLE:
            status = "устарел"
        elif not _fresh(best["checked_at"], clock, urgent):
            status = "устарел"
        elif best["source_type"] in ("official", "university") and best["cycle"] == TARGET_CYCLE:
            status = "подтверждён"
        else:
            status = "вероятен"
    return {"working": {"date": best["value"], **_public(best)}, "status": status,
            "cycle_status": cycle_status(as_label), "outcome": deadline_outcome(as_label), "urgent": urgent,
            "alternatives": [_public(f) for f in others]}


def _resolve_amount(facts: list[dict], clock: str) -> dict:
    if not facts:
        return {"working": None, "status": "не указано", "outcome": "not_stated", "alternatives": []}
    facts = sorted(facts, key=lambda f: (_cycle_rank(f["cycle"]), SOURCE_RANK[f["source_type"]], f["checked_at"]), reverse=True)
    best = facts[0]
    same_rank = [f for f in facts[1:] if SOURCE_RANK[f["source_type"]] >= SOURCE_RANK[best["source_type"]]
                 and _cycle_rank(f["cycle"]) == _cycle_rank(best["cycle"]) and f["value"] != best["value"]]
    status = ("конфликт" if same_rank else
              "подтверждён" if best["source_type"] in ("official", "university") and _fresh(best["checked_at"], clock, False)
              else "вероятен")
    return {"working": _public(best), "status": status, "alternatives": [_public(f) for f in facts[1:]]}
