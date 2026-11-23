"""Метрики извлечения на A2 (design doc 3.1): M4, M5, M6, M8(а). Считаются кодом, без judge.

Формат предсказания системы для задачи extract:
{
  "application_deadlines": [{"date", "granularity", "cycle", "scope", "scope_detail", "quote", "page", "source_url", "checked_at"}],
  "amount": null | {"value", "currency", "period", "full_coverage", "quote", "page", "source_url", "checked_at"}
}
Статус цикла системы всегда пересчитывается здесь же правилом rules.cycle_status — модель его не ставит.
Предсказание и эталон перед сравнением проходят одну и ту же нормализацию (rules.norm_deadline / norm_amount) —
ту же, что используют системы. Исходы «цикл неизвестен» и «не указано на странице» отчитываются раздельно.
"""

from __future__ import annotations

import math

from .core import BUDGET, ERROR, PARTIAL, REFUSED
from .rules import (AMOUNT_OUTCOMES, DEADLINE_OUTCOMES, TARGET_CYCLE, amount_outcome, cycle_status,
                    deadline_outcome, norm_amount, norm_deadline, resolve_date)
from .tools import PAGES, norm

PROVENANCE_FIELDS = ("quote", "page", "source_url", "checked_at")


def _dl_key(d: dict) -> tuple:
    return d["date"], d["granularity"], d["scope"]


def _earliest_current(deadlines: list[dict]) -> str | None:
    dates = [resolve_date(d["date"], d.get("cycle")) for d in deadlines if d.get("cycle") == TARGET_CYCLE]
    dates = [x for x in dates if x]
    return min(dates) if dates else None


def _later(a: str, b: str) -> bool:
    """a позже b при сравнении на общей точности ('2027-01' не позже '2027-01-06')."""
    n = min(len(a), len(b))
    return a[:n] > b[:n]


def m4(pred: dict, gt: dict) -> dict:
    p_dl = [norm_deadline(d) for d in pred.get("application_deadlines") or []]
    g_dl = [norm_deadline(d) for d in gt["application_deadlines"]]
    p_status, g_status = cycle_status(p_dl), gt["cycle_status"]
    g_outcome = deadline_outcome(g_dl)
    status_ok = p_status == g_status
    set_ok = {_dl_key(d) for d in p_dl} == {_dl_key(d) for d in g_dl}
    danger = None
    if p_status == "published" and g_outcome == "not_stated":
        danger = "invented"            # выдуман дедлайн там, где на странице его нет
    elif p_status == "published" and g_outcome == "cycle_unknown":
        danger = "year_guessed"        # дата есть, но цикл из страницы не следует — система достроила год
    elif p_status == "published" and g_status == "only_past_cycle":
        danger = "past_as_current"     # дата прошлого цикла выдана за текущую
    elif p_status == "published" and g_status == "published":
        p, g = _earliest_current(p_dl), _earliest_current(g_dl)
        if p and g and _later(p, g):
            danger = "later_than_real"
    return {"correct": status_ok and set_ok, "status_ok": status_ok, "set_ok": set_ok,
            "pred_status": p_status, "gt_status": g_status, "gt_outcome": g_outcome,
            "pred_outcome": deadline_outcome(p_dl), "danger": danger}


def m5(pred: dict, gt: dict) -> dict:
    p, g = norm_amount(pred.get("amount")), norm_amount(gt["amount"])
    g_outcome, p_outcome = amount_outcome(g), amount_outcome(p)
    base = {"gt_has_amount": g_outcome != "not_stated", "gt_outcome": g_outcome, "pred_outcome": p_outcome}
    if g_outcome == "not_stated":
        return {"correct": p_outcome == "not_stated", **base}
    if g_outcome == "full_coverage_only":
        return {"correct": p is not None and p["full_coverage"] is True, **base}
    ok = (p is not None and p["value"] is not None and math.isclose(p["value"], g["value"], rel_tol=0.01)
          and p["currency"] == g["currency"] and p["period"] == g["period"])
    return {"correct": ok, **base}


def _facts(pred: dict) -> list[dict]:
    facts = list(pred.get("application_deadlines") or [])
    if pred.get("amount"):
        facts.append(pred["amount"])
    return facts


def m6_m8(pred: dict, page_cache: dict[str, str]) -> dict:
    """M6: у факта есть цитата, страница, URL, дата проверки. M8(а): цитата не найдена в снимке L0."""
    facts = _facts(pred)
    with_prov = sum(all(f.get(k) for k in PROVENANCE_FIELDS) for f in facts)
    ungrounded = 0
    for f in facts:
        page = f.get("page")
        if not page or not f.get("quote"):
            ungrounded += 1
            continue
        if page not in page_cache:
            path = PAGES / page
            page_cache[page] = norm(path.read_text(encoding="utf-8")) if path.exists() else ""
        if norm(f["quote"]) not in page_cache[page]:
            ungrounded += 1
    return {"facts": len(facts), "with_provenance": with_prov, "ungrounded": ungrounded}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(c - h, 3), round(c + h, 3)


def _share(xs: list[bool]) -> str | None:
    return f"{sum(xs)}/{len(xs)}" if xs else None


def score_extract(results: list, labels: dict[str, dict]) -> tuple[list[dict], dict]:
    per_task, cache = [], {}
    for r in results:
        gt = labels[r.task_id]
        failed = r.status in (ERROR, REFUSED)
        incomplete = r.status in (PARTIAL, BUDGET)
        pred = {} if failed else r.output
        deadline_score, amount_score = m4(pred, gt), m5(pred, gt)
        if failed or (incomplete and not pred.get("application_deadlines")):
            deadline_score.update(correct=False, status_ok=False, set_ok=False)
        if failed or (incomplete and not pred.get("amount")):
            amount_score["correct"] = False
        row = {"id": r.task_id, "status": r.status, "m4": deadline_score, "m5": amount_score, **m6_m8(pred, cache)}
        per_task.append(row)
    n = len(per_task)
    k4 = sum(x["m4"]["correct"] for x in per_task)
    k5 = sum(x["m5"]["correct"] for x in per_task)
    n5a = [x for x in per_task if x["m5"]["gt_has_amount"]]
    facts = sum(x["facts"] for x in per_task)
    dangers: dict[str, int] = {}
    for x in per_task:
        if x["m4"]["danger"]:
            dangers[x["m4"]["danger"]] = dangers.get(x["m4"]["danger"], 0) + 1
    agg = {
        "n": n,
        "M4": round(k4 / n, 3), "M4_ci95": wilson(k4, n),
        "M4_status_acc": round(sum(x["m4"]["status_ok"] for x in per_task) / n, 3),
        "M4_set_acc": round(sum(x["m4"]["set_ok"] for x in per_task) / n, 3),
        "M4_with_dates": _share([x["m4"]["correct"] for x in per_task if x["m4"]["gt_outcome"] != "not_stated"]),
        "M4_no_dates": _share([x["m4"]["correct"] for x in per_task if x["m4"]["gt_outcome"] == "not_stated"]),
        "M4_by_outcome": {o: _share([x["m4"]["correct"] for x in per_task if x["m4"]["gt_outcome"] == o])
                          for o in DEADLINE_OUTCOMES},
        "M5_by_outcome": {o: _share([x["m5"]["correct"] for x in per_task if x["m5"]["gt_outcome"] == o])
                          for o in AMOUNT_OUTCOMES},
        "M4_dangerous": sum(dangers.values()), "M4_dangerous_per_100": round(100 * sum(dangers.values()) / n, 1),
        "M4_dangerous_by_type": dangers,
        "M5": round(k5 / n, 3), "M5_ci95": wilson(k5, n),
        "M5_on_stated": round(sum(x["m5"]["correct"] for x in n5a) / len(n5a), 3) if n5a else None,
        "M6": round(sum(x["with_provenance"] for x in per_task) / facts, 3) if facts else None,
        "M8a": round(sum(x["ungrounded"] for x in per_task) / facts, 3) if facts else None,
        "facts": facts,
        "status_counts": {s: sum(x["status"] == s for x in per_task) for s in {x["status"] for x in per_task}},
    }
    return per_task, agg
