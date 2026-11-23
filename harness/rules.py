"""Правила, которые считает код, а не модель (design doc 2.1, «Статус цикла»). Общие для систем и оценщика.

Здесь же — нормализация значений (дата, валюта, период выплаты, полное покрытие) и исходы «что известно о поле».
Её вызывают и системы (B1, LLM-извлечение, тетрадь), и метрики — для предсказания и для эталона одинаково,
поэтому расхождение в написании («€» / «EUR», «monthly» / «month») не считается ни ошибкой, ни совпадением случайно.
"""

from __future__ import annotations

import re

TARGET_CYCLE = "2027/28"

GRANULARITY_RX = {"day": r"^\d{4}-\d{2}-\d{2}$", "month": r"^\d{4}-\d{2}$", "day_no_year": r"^--\d{2}-\d{2}$"}

CURRENCY = {"€": "EUR", "euro": "EUR", "euros": "EUR", "£": "GBP", "pound": "GBP", "pounds": "GBP",
            "$": "USD", "us$": "USD", "c$": "CAD", "ca$": "CAD", "chf": "CHF", "fr.": "CHF",
            "sek": "SEK", "kr": None, "dkk": "DKK", "nok": "NOK", "huf": "HUF", "czk": "CZK", "pln": "PLN"}
PERIOD = {"month": "month", "monthly": "month", "per month": "month", "a month": "month", "/month": "month",
          "semester": "semester", "per semester": "semester", "a semester": "semester",
          "year": "year", "yearly": "year", "annual": "year", "annually": "year", "per year": "year",
          "a year": "year", "per annum": "year", "/year": "year",
          "total": "total", "one-off": "total", "one-time": "total", "lump sum": "total"}

# Исходы поля. «Не указано на странице» — это незнание, а не «не существует»: дедлайна может не быть
# на снимке, но он есть в реальности. «Стипендия не найдена» (поиск пуст) — отдельный исход на уровне агента.
DEADLINE_OUTCOMES = ("published", "only_past_cycle", "cycle_unknown", "not_stated")
AMOUNT_OUTCOMES = ("stated", "full_coverage_only", "not_stated")


# ---------- нормализация ----------

def norm_currency(c: str | None) -> str | None:
    if not c or not str(c).strip():
        return None
    s = str(c).strip()
    if s.lower() in CURRENCY:
        return CURRENCY[s.lower()]
    return s.upper() if re.fullmatch(r"[A-Za-z]{3}", s) else None


def norm_period(p: str | None) -> str | None:
    if not p or not str(p).strip():
        return None
    return PERIOD.get(" ".join(str(p).lower().split()))


def norm_amount(a: dict | None) -> dict | None:
    """Сумма к общему виду: value — float или None, валюта — ISO 4217, период — month/semester/year/total,
    full_coverage — True / False / None (None = «страница не говорит», False = «прямо сказано: частичное»)."""
    if a is None:
        return None
    v = a.get("value")
    try:
        v = None if v is None else float(v)
    except (TypeError, ValueError):
        v = None
    fc = a.get("full_coverage")
    return {**a, "value": v, "currency": norm_currency(a.get("currency")), "period": norm_period(a.get("period")),
            "full_coverage": fc if fc in (True, False) else None}


def norm_deadline(d: dict) -> dict:
    """Дата без пробелов; точность обязана соответствовать формату (иначе дата не сравнивается); область по умолчанию global."""
    date = str(d.get("date") or "").strip()
    gran = d.get("granularity")
    if not re.match(GRANULARITY_RX.get(gran, "^$"), date):
        gran = next((g for g, rx in GRANULARITY_RX.items() if re.match(rx, date)), None)
    return {**d, "date": date, "granularity": gran, "scope": d.get("scope") or "global",
            "cycle": d.get("cycle") or None}


# ---------- статусы и исходы ----------

def cycle_status(application_deadlines: list[dict]) -> str:
    """Статус цикла по контракту (3 значения): published — есть дедлайн подачи цикла 2027/28;
    only_past_cycle — есть только дедлайны прошлых циклов; not_found — подтверждения для 2027/28 нет
    (дедлайнов на странице нет или у всех цикл неизвестен; год не достраиваем). Подробнее — deadline_outcome."""
    cycles = {d.get("cycle") for d in application_deadlines}
    if TARGET_CYCLE in cycles:
        return "published"
    if any(c and c < TARGET_CYCLE for c in cycles):
        return "only_past_cycle"
    return "not_found"


def deadline_outcome(application_deadlines: list[dict]) -> str:
    """Как cycle_status, но not_found разделён: cycle_unknown — дата на странице есть, цикл из страницы не следует;
    not_stated — дедлайна подачи на странице нет (неизвестно, а не «не существует»)."""
    status = cycle_status(application_deadlines)
    if status != "not_found":
        return status
    return "cycle_unknown" if application_deadlines else "not_stated"


def amount_outcome(a: dict | None) -> str:
    a = norm_amount(a)
    if a is None:
        return "not_stated"
    if a["value"] is not None:
        return "stated"
    return "full_coverage_only" if a["full_coverage"] is True else "not_stated"


def resolve_date(date: str, cycle: str | None) -> str | None:
    """Дата для сравнения 'раньше/позже'. '--MM-DD' достраивается только по известному циклу:
    приём на цикл 2027/28 идёт с сентября 2026 по август 2027."""
    if not date.startswith("--"):
        return date
    if not cycle:
        return None
    start = int(cycle[:4]) - 1
    month = int(date[2:4])
    return f"{start if month >= 9 else start + 1}-{date[2:]}"
