"""Оркестратор тетради (design doc, раздел 4): discovery → загрузка → извлечение → валидатор → L1 → L2.

Многошаговость и поведение на сбоях задаются здесь кодом, а не моделью:
- fetch: http_5xx/timeout → до 2 ретраев; http_403/stub_page/исчерпаны ретраи → fetch_alt;
  оба не смогли → последний снимок L0 с его датой (деградация) или запись в «кандидаты» с причиной;
- extract_llm: invalid_json — 1 повтор (внутри экстрактора), затем страница в «кандидаты» с флагом;
- запись в L1 по стипендии атомарна: при остановке по бюджету посреди стипендии в тетради нет «половины карточки»;
- бюджет: при исчерпании раннер возвращает ctx.partial — отчёт «что сделано / что осталось».
"""

from __future__ import annotations

import json
from pathlib import Path

from .core import Context
from .notebook import Notebook
from .systems.llm_extract import PROMPT_SHA, _invalid
from .tools import ROOT, Page, ToolError, norm


# ---------- экстракторы: одинаковый интерфейс page -> {"dates": [...], "amount": {...}|None} ----------

class ReplayExtractor:
    """Заглушка модели для сценариев без API-ключа: отдаёт то, что извлекла бы «идеальная модель» (эталон
    видимой части), плюс явно заданные ответы для отдельных страниц. Проверяет оркестрацию, а не качество модели;
    метрики качества на ней не считаются."""
    name = "replay"
    prompt_sha = "replay-gt-v1"

    def __init__(self, overrides: dict[str, dict] | None = None):
        self.overrides = overrides or {}
        self.labels = {}
        for line in (ROOT / "eval" / "gt" / "labels_a.jsonl").read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                lab = json.loads(line)
                self.labels[lab["id"]] = lab

    def __call__(self, ctx: Context, page: Page) -> dict:
        for attempt in range(2):            # тот же контракт, что у LLMExtract: invalid_json — 1 повтор
            ctx.meter.step()
            try:
                ctx.tools.guard("extract_llm", page.page)
                break
            except ToolError as e:
                if e.code != "invalid_json" or attempt == 1:
                    raise
                ctx.log("retry", tool="extract_llm", page=page.page, code=e.code)
        if page.page in self.overrides:
            return self.overrides[page.page]
        lab = self.labels.get(page.page.split("/")[0])
        if not lab:
            return {"dates": [], "amount": None}
        keys = ("date", "granularity", "cycle", "scope", "scope_detail", "quote")
        dates = [{k: d[k] for k in keys} | {"type": "application"} for d in lab["application_deadlines"] if d["page"] == page.page]
        dates += [{k: d.get(k, "global" if k == "scope" else None) for k in keys} | {"type": d["type"]}
                  for d in lab["other_dates"] if d["page"] == page.page]
        a = lab["amount"]
        amount = {k: a[k] for k in ("value", "currency", "period", "full_coverage", "quote")} if a and a["page"] == page.page else None
        return {"dates": dates, "amount": amount}


class LLMExtractor:
    name = "llm"
    prompt_sha = PROMPT_SHA

    def __init__(self, llm):
        self.llm = llm

    def __call__(self, ctx: Context, page: Page) -> dict:
        return self.llm._call(ctx, page.page, page.url, page.text)


# ---------- агент ----------

class NotebookAgent:
    def __init__(self, notebook: Notebook, extractor):
        self.nb, self.extract = notebook, extractor

    # --- получение страницы: ретраи → запасной путь → последний снимок ---
    def get_page(self, ctx: Context, page: str) -> tuple[Page | None, str]:
        tools = ctx.tools
        for attempt in range(3):            # 1 попытка + 2 ретрая
            try:
                p = tools.fetch(page)
                return p, "fetch" if attempt == 0 else f"fetch_retry{attempt}"
            except ToolError as e:
                if e.retryable and attempt < 2:
                    ctx.log("retry", tool="fetch", page=page, code=e.code, attempt=attempt + 1)
                    continue
                ctx.log("fallback", tool="fetch", page=page, code=e.code)
                break
        try:
            return tools.fetch_alt(page), "fetch_alt"
        except ToolError as e:
            ctx.log("fallback_failed", tool="fetch_alt", page=page, code=e.code)
        text, when = self.nb.page_text(page), self.nb.last_fetch(page)
        if text:
            ctx.log("degraded", page=page, using_snapshot_from=when)
            return Page(page, "", text, "", when), "last_snapshot"
        return None, "unavailable"

    # --- загрузка и извлечение одной стипендии (атомарная запись в L1) ---
    def ingest(self, ctx: Context, sid: str, pages: list[str] | None = None, source_type: str = "official") -> dict:
        report = {"scholarship_id": sid, "pages": [], "facts_new": 0, "rejected": 0, "candidates": [], "status": "ok"}
        pages = pages or ctx.tools.list_pages(sid)
        staged = []
        for page in pages:
            p, how = self.get_page(ctx, page)
            if p is None:
                report["candidates"].append({"page": page, "reason": "страница недоступна: fetch и fetch_alt не смогли, снимка нет"})
                report["pages"].append({"page": page, "via": how})
                continue
            if how == "last_snapshot":
                report["pages"].append({"page": page, "via": how, "snapshot_from": p.fetched_at})
                report["status"] = "degraded"
                continue                    # факты прошлого снимка уже в L1 с их датой проверки — дату не освежаем
            sha, changed = self.nb.put_page(page, p.url, p.text, p.fetched_at, "own_fetch" if how.startswith("fetch") and how != "fetch_alt" else how)
            data = None if changed else self.nb.cached_extract(sha, self.extract.prompt_sha)
            if data is None:
                try:
                    data = self.extract(ctx, p)
                except ToolError as e:
                    report["candidates"].append({"page": page, "reason": f"извлечение не удалось: {e.code}"})
                    report["pages"].append({"page": page, "via": how, "extract": e.code})
                    continue
                self.nb.cache_extract(sha, self.extract.prompt_sha, data)
            else:
                ctx.log("cache_hit", page=page)
            report["pages"].append({"page": page, "via": how, "changed": changed})
            ntext = norm(p.text)
            for d in data.get("dates", []):
                if _invalid(d, ntext):
                    report["rejected"] += 1
                    continue
                field = "application_deadline" if d["type"] == "application" else f"date_{d['type']}"
                staged.append(dict(sid=sid, field=field, value=d["date"], source_type=source_type, quote=d["quote"],
                                   page=page, source_url=p.url, checked_at=p.fetched_at, cycle=d["cycle"],
                                   scope=d["scope"], scope_detail=d["scope_detail"]))
            a = data.get("amount")
            if a and norm(a["quote"]) in ntext:
                staged.append(dict(sid=sid, field="amount", value={k: a[k] for k in ("value", "currency", "period", "full_coverage")},
                                   source_type=source_type, quote=a["quote"], page=page, source_url=p.url,
                                   checked_at=p.fetched_at))
            elif a:
                report["rejected"] += 1
        with self.nb.db:                    # атомарно: всё по стипендии или ничего
            for f in staged:
                _, created = self.nb.add_fact(f.pop("sid"), f.pop("field"), f.pop("value"), **f)
                report["facts_new"] += created
            report["card"] = self.nb.recompute(sid)
        if report["candidates"] and report["status"] == "ok":
            report["status"] = "partial"
        ctx.log("ingested", sid=sid, facts_new=report["facts_new"], status=report["status"])
        return report

    # --- discovery: шаг 2 зависит от результата шага 1 ---
    def discover(self, ctx: Context, lead: str) -> dict:
        try:
            hits = ctx.tools.search(lead)
        except ToolError as exc:
            if exc.code not in {"timeout", "rate_limit"}:
                raise
            ctx.log("retry", tool="search", arg=lead, code=exc.code)
            hits = ctx.tools.search(lead)
        if not hits:
            ctx.log("not_found", lead=lead)
            return {"lead": lead, "status": "не найдено", "records": 0}
        sid = hits[0]["scholarship_id"]
        rep = self.ingest(ctx, sid)
        return {"lead": lead, "status": rep["status"], "scholarship_id": sid, "records": 1, "report": rep}

    def discover_batch(self, ctx: Context, leads: list[str]) -> dict:
        state = {"done": [], "remaining": list(leads), "not_found": [], "stopped": None}
        ctx.partial = state                  # при BudgetExceeded раннер вернёт именно это
        for lead in leads:
            res = self.discover(ctx, lead)
            state["remaining"].remove(lead)
            (state["done"] if res["records"] else state["not_found"]).append(
                {"lead": lead, "scholarship_id": res.get("scholarship_id"), "status": res["status"]})
        return state

    # --- ответ по тетради (без модели): что показали бы пользователю ---
    def answer_fact(self, sid: str, field: str = "deadline") -> dict:
        card = self.nb.card(sid) or self.nb.recompute(sid)
        block = card[field]
        w = block["working"]
        return {"scholarship_id": sid, "field": field, "status": block["status"],
                "value": (w.get("date") or w.get("value")) if w else None,
                "source": w and w["source_type"], "checked_at": w and w["checked_at"],
                "shown_alternatives": [(a["value"], a["source_type"]) for a in block["alternatives"]]}


def load_profile(name: str) -> dict:
    path = Path(__file__).parent / "profiles.json"
    return json.loads(path.read_text(encoding="utf-8"))[name]
