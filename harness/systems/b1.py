"""Baseline B1 «поиск + правила» (design doc 8.1): без LLM, регулярные выражения по тексту страниц.

- дедлайн: первая дата рядом со словами deadline / closing date / apply by / applications close;
  цикл — по году даты (сентябрь 2026 – август 2027 → 2027/28), без года — цикл неизвестен; область всегда global;
- сумма: первое число с валютой рядом с per month / per year / monthly / annually; «fully funded» → полное покрытие;
- статус цикла считает общий код (harness.rules), как и у системы.
Конфликты, исправления и память не поддерживаются.
"""

from __future__ import annotations

import re

from ..core import OK, PARTIAL, Context, Task
from ..tools import ToolError

VERSION = "b1-2026-11-21"

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
     "november", "december"], 1)}
MON = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
KEYWORD = re.compile(r"deadline|closing date|apply by|applications? (?:close|closes|must be (?:submitted|received))"
                     r"|due date|submission date", re.I)
DATE_PATTERNS = [
    # 6 January 2027 / 6th of January, 2027 / 6 January
    (re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?{MON},?(?:\s+(20\d{{2}}))?", re.I), "dmy"),
    # January 6, 2027 / January 6
    (re.compile(rf"\b{MON}\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(20\d{{2}}))?", re.I), "mdy"),
    (re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b"), "iso"),
    (re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(20\d{2})\b"), "dot"),
]
WINDOW = 200

CUR = r"(€|£|\$|EUR|GBP|USD|SEK|CHF|CAD|DKK|NOK|HUF|CZK|PLN)"
CUR_MAP = {"€": "EUR", "£": "GBP", "$": "USD"}
AMOUNT = [re.compile(rf"{CUR}\s?(\d[\d,.\s]*\d|\d)", re.I), re.compile(rf"(\d[\d,.\s]*\d|\d)\s?{CUR}", re.I)]
PERIOD = re.compile(r"per month|a month|monthly|/month|per year|a year|annually|per annum|yearly|/year", re.I)
FULL = re.compile(r"fully[- ]funded|full scholarship|covers? (?:the )?full tuition", re.I)


def _first_date(text: str) -> tuple[str, str, int, int] | None:
    """(date, granularity, start, end) первой даты в тексте."""
    best = None
    for rx, kind in DATE_PATTERNS:
        m = rx.search(text)
        if not m or (best and m.start() >= best[2]):
            continue
        try:
            if kind == "dmy":
                d, mon, y = int(m.group(1)), MONTHS[m.group(2).lower()], m.group(3)
            elif kind == "mdy":
                mon, d, y = MONTHS[m.group(1).lower()], int(m.group(2)), m.group(3)
            elif kind == "iso":
                y, mon, d = m.group(1), int(m.group(2)), int(m.group(3))
            else:
                d, mon, y = int(m.group(1)), int(m.group(2)), m.group(3)
        except (KeyError, ValueError):
            continue
        if not (1 <= d <= 31 and 1 <= mon <= 12):
            continue
        date, gran = (f"{y}-{mon:02d}-{d:02d}", "day") if y else (f"--{mon:02d}-{d:02d}", "day_no_year")
        best = (date, gran, m.start(), m.end())
    return best


def _cycle(date: str) -> str | None:
    if date.startswith("--"):
        return None
    y, m = int(date[:4]), int(date[5:7])
    start = y if m >= 9 else y - 1      # приём на цикл Y/Y+1 идёт с сентября Y-1 по август Y
    return f"{start + 1}/{str(start + 2)[2:]}"


def _quote(text: str, a: int, b: int) -> str:
    return " ".join(text[max(0, a):min(len(text), b)].split())


def _amount_value(s: str) -> float | None:
    s = s.replace(" ", "").replace(" ", "")
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", s):
        s = s.replace(",", "")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


class B1:
    name = "b1"

    def config(self) -> dict:
        return {"model": None, "version": VERSION, "temperature": None, "seed": None,
                "rules": {"keyword": KEYWORD.pattern, "window_chars": WINDOW, "period": PERIOD.pattern}}

    def run(self, task: Task, ctx: Context) -> tuple[str, dict]:
        tools = ctx.tools
        sid = task.input["scholarship_id"]
        out = {"application_deadlines": [], "amount": None, "pages_read": [], "pages_failed": []}
        ctx.partial = out
        for page in tools.list_pages(sid):
            ctx.meter.step()
            try:
                p = tools.fetch(page)
            except ToolError as e:
                out["pages_failed"].append({"page": page, "error": e.code})
                continue
            out["pages_read"].append(page)
            prov = {"page": p.page, "source_url": p.url, "checked_at": p.fetched_at}
            text = p.text
            if not out["application_deadlines"]:
                for km in KEYWORD.finditer(text):
                    found = _first_date(text[km.start():km.end() + WINDOW])
                    if found:
                        date, gran, a, b = found
                        out["application_deadlines"].append({
                            "date": date, "granularity": gran, "cycle": _cycle(date), "scope": "global",
                            "scope_detail": None, "quote": _quote(text, km.start(), km.start() + b), **prov})
                        break
            if out["amount"] is None:
                for pm in PERIOD.finditer(text):
                    lo = max(0, pm.start() - 80)
                    window = text[lo:pm.start()]
                    cands = [m for rx in AMOUNT for m in rx.finditer(window)]
                    if not cands:
                        continue
                    m = max(cands, key=lambda m: m.end())
                    groups = [g for g in m.groups() if g]
                    cur = next(g for g in groups if re.fullmatch(CUR, g, re.I))
                    val = _amount_value(next(g for g in groups if g is not cur))
                    if val is None:
                        continue
                    per = pm.group(0).lower()
                    period = "month" if "month" in per else "year"
                    out["amount"] = {"value": val, "currency": CUR_MAP.get(cur, cur.upper()), "period": period,
                                     "full_coverage": None, "variants": None,
                                     "quote": _quote(text, lo + m.start(), pm.end()), **prov}
                    break
            if out["amount"] is None and (fm := FULL.search(text)):
                out["amount"] = {"value": None, "currency": None, "period": None, "full_coverage": True,
                                 "variants": None, "quote": _quote(text, fm.start(), fm.end() + 20), **prov}
        return (PARTIAL if out["pages_failed"] else OK), out
