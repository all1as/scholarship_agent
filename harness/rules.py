"""Правила, которые считает код, а не модель (design doc 2.1, «Статус цикла»). Общие для всех систем."""

TARGET_CYCLE = "2027/28"


def cycle_status(application_deadlines: list[dict]) -> str:
    """published — есть дедлайн подачи цикла 2027/28; only_past_cycle — есть только дедлайны прошлых циклов;
    not_found — дедлайнов подачи нет или у всех цикл неизвестен (год не достраиваем)."""
    cycles = {d.get("cycle") for d in application_deadlines}
    if TARGET_CYCLE in cycles:
        return "published"
    if any(c and c < TARGET_CYCLE for c in cycles):
        return "only_past_cycle"
    return "not_found"


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
