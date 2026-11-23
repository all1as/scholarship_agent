"""Инструменты и их контракты (design doc, раздел 5).

У каждого инструмента: сигнатура, типизированные ошибки, таймаут, лимит вызовов на задачу.
Ошибка — всегда ToolError с кодом из списка контракта, а не текст «что-то пошло не так».

Офлайн-режим (eval): fetch читает снимки L0 из eval/gt/pages, today() возвращает дату заморозки eval-набора.
Сбои для сценариев задаются через faults: {"fetch": {"chevening/2.txt": "http_403"}}.
"""

from __future__ import annotations

import csv
import hashlib
import re
import time
from dataclasses import dataclass
from pathlib import Path

from .core import Context

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "eval" / "gt" / "pages"
EVAL_DATE = "2026-10-25"   # дата заморозки eval v1: от неё считаются «ближайшие» и «закрывшиеся»


@dataclass(frozen=True)
class ToolSpec:
    name: str
    signature: str
    returns: str
    errors: tuple[str, ...]
    timeout_s: float
    max_calls: int          # на одну задачу
    retry: str              # кто и как ретраит


CONTRACTS: dict[str, ToolSpec] = {
    "list_pages": ToolSpec(
        "list_pages", "list_pages(scholarship_id: str) -> list[str]",
        "пути снимков L0 стипендии ('<id>/<n>.txt'), основная страница первой",
        ("not_found", "timeout", "call_limit"), timeout_s=1, max_calls=3, retry="нет: ошибка детерминированная"),
    "fetch": ToolSpec(
        "fetch", "fetch(page: str) -> Page(text, url, sha256, fetched_at, page)",
        "текст страницы после trafilatura + метаданные снимка",
        ("not_found", "http_403", "http_5xx", "timeout", "stub_page", "call_limit"),
        timeout_s=20, max_calls=8,
        retry="http_5xx/timeout — до 2 ретраев (делает система); http_403/stub_page — без ретрая, запасной путь"),
    "fetch_alt": ToolSpec(
        "fetch_alt", "fetch_alt(page: str) -> Page", "запасной путь получения текста (Tavily Extract); в офлайне — тот же снимок",
        ("not_found", "http_403", "timeout", "call_limit"), timeout_s=30, max_calls=4,
        retry="нет: это уже запасной путь; при ошибке — последний снимок L0 с датой или запись в 'кандидаты'"),
    "search": ToolSpec(
        "search", "search(query: str) -> list[Hit(scholarship_id, name, url, score)]",
        "кандидаты официальной страницы по названию (в офлайне — по названиям и синонимам снимков); пустой список = не найдено",
        ("timeout", "rate_limit", "call_limit"), timeout_s=15, max_calls=15,
        retry="timeout/rate_limit — 1 ретрай; пустая выдача — не ошибка, а ответ «не найдено»"),
    "extract_llm": ToolSpec(
        "extract_llm", "extract_llm(page_text: str, url: str) -> dict (JSON по схеме)",
        "факты страницы по JSON-схеме, у каждого значения цитата",
        ("invalid_json", "timeout", "rate_limit", "provider_error", "call_limit"),
        timeout_s=60, max_calls=6,
        retry="invalid_json — 1 повтор, затем страница в 'кандидаты' с флагом; rate_limit/timeout — 2 ретрая с backoff"),
    "today": ToolSpec(
        "today", "today() -> str (YYYY-MM-DD)", "текущая дата (в eval — дата заморозки набора)",
        ("timeout", "call_limit"), timeout_s=1, max_calls=50, retry="не нужен"),
}


class ToolError(Exception):
    def __init__(self, tool: str, code: str, detail: str = ""):
        spec = CONTRACTS.get(tool)
        assert spec is None or code in spec.errors, f"{tool}: код ошибки {code} не из контракта"
        super().__init__(f"{tool}:{code} {detail}".strip())
        self.tool, self.code, self.detail = tool, code, detail

    @property
    def retryable(self) -> bool:
        return self.code in {"http_5xx", "timeout", "rate_limit", "provider_error"}


@dataclass(frozen=True)
class Page:
    page: str
    url: str
    text: str
    sha256: str
    fetched_at: str


def _manifest() -> dict[str, dict]:
    with open(PAGES / "manifest.csv", encoding="utf-8-sig") as f:
        return {f"{r['id']}/{r['n']}.txt": r for r in csv.DictReader(f)}


STUB_MARKERS = re.compile(r"captcha|verify you are (a )?human|enable javascript|access denied", re.I)


class Toolbox:
    """Обёртка над инструментами: учёт вызовов в Meter, лимиты из контракта, трейс, инъекция сбоев."""

    def __init__(self, ctx_getter, faults: dict | None = None, allowed_ids: set[str] | None = None,
                 limits: dict[str, int] | None = None):
        self._ctx_getter = ctx_getter       # Context текущей задачи
        self._faults = faults or {}
        self._calls: dict[str, int] = {}
        self._arg_calls: dict[tuple[str, str], int] = {}
        self._manifest = _manifest()
        self._allowed = allowed_ids        # защита от чтения отложенной части
        self._limits = limits or {}        # переопределение лимитов вызовов (многостипендийные задачи)

    # --- служебное ---
    def _enter(self, tool: str, arg: str) -> Context:
        ctx: Context = self._ctx_getter()
        spec = CONTRACTS[tool]
        n = self._calls.get(tool, 0) + 1
        self._calls[tool] = n
        ctx.meter.tool_call()
        ctx.log("tool_call", tool=tool, arg=arg, n=n)
        limit = self._limits.get(tool, spec.max_calls)
        if n > limit:
            raise ToolError(tool, "call_limit", f"{n}>{limit}")
        ctx.meter.check()
        fault = self._faults.get(tool, {}).get(arg)
        if fault:
            k = self._arg_calls[(tool, arg)] = self._arg_calls.get((tool, arg), 0) + 1
            # строка — сбой на каждом вызове; список — сценарий по попыткам: ["http_5xx", "http_5xx", None] (None = успех)
            fault_code = fault if isinstance(fault, str) else fault[min(k, len(fault)) - 1]
            if fault_code:
                ctx.log("tool_error", tool=tool, arg=arg, code=fault_code, injected=True)
                raise ToolError(tool, fault_code, "injected")
        return ctx

    def guard(self, tool: str, arg: str) -> Context:
        """Учёт, лимит и инъекция сбоев для инструмента, реализованного вне Toolbox (например, вызов LLM)."""
        return self._enter(tool, arg)

    def calls(self) -> dict[str, int]:
        return dict(self._calls)

    # --- инструменты ---
    def _check_timeout(self, tool: str, started: float) -> None:
        if time.perf_counter() - started > CONTRACTS[tool].timeout_s:
            raise ToolError(tool, "timeout")

    def today(self) -> str:
        started = time.perf_counter()
        self._enter("today", "")
        self._check_timeout("today", started)
        return EVAL_DATE

    def list_pages(self, scholarship_id: str) -> list[str]:
        started = time.perf_counter()
        ctx = self._enter("list_pages", scholarship_id)
        if self._allowed is not None and scholarship_id not in self._allowed:
            raise ToolError("list_pages", "not_found", "id вне видимой части")
        pages = sorted((p for p in self._manifest if p.startswith(scholarship_id + "/")
                        and re.fullmatch(r"\d+\.txt", p.split("/")[1])),
                       key=lambda p: int(p.split("/")[1].split(".")[0]))
        if not pages:
            raise ToolError("list_pages", "not_found", scholarship_id)
        self._check_timeout("list_pages", started)
        ctx.log("tool_ok", tool="list_pages", n=len(pages))
        return pages

    def fetch(self, page: str) -> Page:
        ctx = self._enter("fetch", page)
        sid = page.split("/")[0]
        if self._allowed is not None and sid not in self._allowed:
            raise ToolError("fetch", "not_found", "id вне видимой части")
        row = self._manifest.get(page)
        path = PAGES / page
        if row is None or not path.exists():
            raise ToolError("fetch", "not_found", page)
        t = time.perf_counter()
        text = path.read_text(encoding="utf-8")
        self._check_timeout("fetch", t)
        if len(text) < 200 or (len(text) < 3000 and STUB_MARKERS.search(text)):
            ctx.log("tool_error", tool="fetch", arg=page, code="stub_page")
            raise ToolError("fetch", "stub_page", page)
        ctx.log("tool_ok", tool="fetch", page=page, chars=len(text))
        return Page(page, row["url"], text, hashlib.sha256(text.encode("utf-8")).hexdigest(), row["fetched_at"])


    def fetch_alt(self, page: str) -> Page:
        self._enter("fetch_alt", page)
        row = self._manifest.get(page)
        if (self._allowed is not None and page.split("/")[0] not in self._allowed
                or row is None or not (PAGES / page).exists()):
            raise ToolError("fetch_alt", "not_found", page)
        started = time.perf_counter()
        text = (PAGES / page).read_text(encoding="utf-8")
        self._check_timeout("fetch_alt", started)
        return Page(page, row["url"], text, hashlib.sha256(text.encode("utf-8")).hexdigest(), row["fetched_at"])

    def search(self, query: str) -> list[dict]:
        """Офлайн-заглушка поиска: совпадение слов запроса с названием стипендии и синонимами из A4.
        Живой режим (Tavily) подключается той же сигнатурой."""
        started = time.perf_counter()
        ctx = self._enter("search", query)
        q = set(re.findall(r"[a-z0-9]+", query.lower())) - {"scholarship", "scholarships", "the", "of", "for", "programme", "program"}
        hits = []
        for sid, names in _names().items():
            if self._allowed is not None and sid not in self._allowed:
                continue
            best = max(len(q & set(re.findall(r"[a-z0-9]+", n.lower()))) / max(1, len(q)) for n in names)
            if best >= 0.6:
                first = f"{sid}/1.txt"
                hits.append({"scholarship_id": sid, "name": names[0], "url": self._manifest.get(first, {}).get("url"),
                             "score": round(best, 2)})
        hits.sort(key=lambda h: -h["score"])
        self._check_timeout("search", started)
        ctx.log("tool_ok", tool="search", hits=len(hits))
        return hits[:5]


_NAMES: dict[str, list[str]] | None = None


def _names() -> dict[str, list[str]]:
    global _NAMES
    if _NAMES is None:
        import json
        _NAMES = {}
        with open(ROOT / "eval" / "gt" / "reference_list.csv", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                _NAMES.setdefault(r["id"], []).append(r["name"])
        dup = ROOT / "eval" / "gt" / "duplicates.jsonl"
        for line in dup.read_text(encoding="utf-8").splitlines() if dup.exists() else []:
            d = json.loads(line)
            if d.get("same") and len(d.get("scholarship_ids", [])) == 1:
                _NAMES.setdefault(d["scholarship_ids"][0], []).extend([d["name_a"], d["name_b"]])
    return _NAMES


def norm(s: str) -> str:
    """Нормализация для проверки цитат — та же, что в eval/scripts/validate.py."""
    return " ".join(re.sub(r"[“”«»\"*|#\[\]]", " ", s).split()).lower()


def contracts_markdown() -> str:
    rows = ["| Инструмент | Сигнатура | Возвращает | Ошибки | Таймаут | Лимит/задачу | Ретраи |",
            "|---|---|---|---|---|---|---|"]
    for s in CONTRACTS.values():
        rows.append(f"| {s.name} | `{s.signature}` | {s.returns} | {', '.join(s.errors) or '—'} | "
                    f"{s.timeout_s:g} с | {s.max_calls} | {s.retry} |")
    return "\n".join(rows)
