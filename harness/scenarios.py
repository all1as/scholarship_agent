"""Многошаговые сценарии (КТ3): прогон через тот же раннер, с бюджетом, сбоями инструментов и метаданными.

  python -m harness.scenarios                       # все сценарии, экстрактор replay (без API)
  python -m harness.scenarios --only S3,S6

Каждый сценарий — последовательность шагов, где важен порядок; проверяется поведение (ретрай, деградация,
частичный результат, разрешение конфликта, отмена), а не только «не упало».
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Callable

from .agent import NotebookAgent, ReplayExtractor, load_profile
from .context import build_context, retrieve
from .core import BUDGET, Budget, Context, OK, Result, Task
from .notebook import Notebook, NotebookError
from .runner import now, run_tasks, save_run
from .tools import _names, norm

EIFFEL_AGG = "| **2027 deadline** | **January 8, 2027** (institutions submit) |"
EIFFEL_WB = "Deadline for the reception of applications by Campus France: January 10, 2023."


def _dl(date, cycle, quote, gran="day", scope="global"):
    return {"date": date, "granularity": gran, "type": "application", "cycle": cycle, "scope": scope,
            "scope_detail": None, "quote": quote}


@dataclass
class Scenario:
    id: str
    title: str
    requirement: str
    run: Callable[[NotebookAgent, Context], dict]
    check: Callable[[Result, NotebookAgent], list[tuple[str, bool, str]]]
    budget: dict | None = None
    faults: dict | None = None
    overrides: dict | None = None


def _events(res: Result, **kv) -> list[dict]:
    return [e for e in res.trace if all(e.get(k) == v for k, v in kv.items())]


# ---------- S1: второй шаг зависит от первого ----------

def s1_run(agent, ctx):
    found = agent.discover(ctx, "Chevening Scholarships")
    missing = agent.discover(ctx, "Hogwarts Wizarding Excellence Scholarship")
    return {"found": found, "missing": missing}


def s1_check(res, agent):
    o = res.output
    order = [e["tool"] for e in res.trace if e["event"] == "tool_call"]
    first_fetch = order.index("fetch") if "fetch" in order else 99
    card = agent.nb.card("chevening")
    w = card["deadline"]["working"]
    offer = agent.nb.facts("chevening", "date_offer_or_documents")
    searches_after_missing = order[order.index("search", 1) + 1:] if order.count("search") > 1 else []
    return [
        ("поиск → список страниц → загрузка (порядок)", order[0] == "search" and order.index("list_pages") < first_fetch, " → ".join(order[:5])),
        ("дедлайн взят с подстраницы timeline (шаг 2 по результату шага 1)", w and w["source_url"] and w["date"] == "2026-10",
         f"{w and w['date']} scope={w and w['scope']}"),
        ("область дедлайна — страна", w and w["scope"] == "country", str(w and w["scope_detail"])),
        ("дата оффера 8 July 2027 не выдана за дедлайн подачи", any(f["value"] == "2027-07-08" for f in offer)
         and w["date"] != "2027-07-08", f"offer facts: {[f['value'] for f in offer]}"),
        ("несуществующая стипендия: «не найдено», 0 записей, без загрузок", o["missing"]["records"] == 0
         and "fetch" not in searches_after_missing, o["missing"]["status"]),
    ]


# ---------- S2: ошибка инструмента посередине ----------

def s2_run(agent, ctx):
    out = {"eiffel": agent.ingest(ctx, "eiffel"),
           "commonwealth": agent.ingest(ctx, "commonwealth_masters"),
           "nl": agent.ingest(ctx, "nl_scholarship")}
    # перепроверка Lund: сначала успешная загрузка, затем сайт и запасной путь недоступны
    agent.ingest(ctx, "lund_global", pages=["lund_global/1.txt"])
    agent.nb.clock = "2026-11-21"           # прошёл почти месяц
    out["lund_recheck"] = agent.ingest(ctx, "lund_global", pages=["lund_global/2.txt"])
    out["cached_recheck"] = agent.ingest(ctx, "lund_global", pages=["lund_global/1.txt"])
    return out


S2_FAULTS = {
    "fetch": {"eiffel/1.txt": ["http_5xx", "http_5xx", None],          # два сбоя, третья попытка успешна
              "commonwealth_masters/1.txt": "http_403",                 # бот заблокирован → запасной путь
              "lund_global/1.txt": [None, "http_403"], "lund_global/2.txt": "http_403"},
    "fetch_alt": {"lund_global/1.txt": "http_403", "lund_global/2.txt": "http_403"},                     # и запасной путь не смог
    "extract_llm": {"nl_scholarship/1.txt": ["invalid_json", "invalid_json"]},  # повтор не помог
}


def s2_check(res, agent):
    o = res.output
    retries = _events(res, event="retry", tool="fetch", page="eiffel/1.txt")
    cw_pages = {p["page"]: p["via"] for p in o["commonwealth"]["pages"]}
    lund = o["lund_recheck"]
    lund_card = agent.nb.card("lund_global")
    nl = o["nl"]
    return s2_cache_checks(res, agent) + [
        ("http_5xx: 2 ретрая, затем успех, дедлайн получен", len(retries) == 2 and o["eiffel"]["card"]["deadline"]["working"]["date"] == "2027-01-06",
         f"retries={len(retries)} via={o['eiffel']['pages'][0]['via']}"),
        ("http_403: без ретраев, запасной путь fetch_alt", cw_pages.get("commonwealth_masters/1.txt") == "fetch_alt"
         and not _events(res, event="retry", page="commonwealth_masters/1.txt"), str(cw_pages)),
        ("invalid_json: 1 повтор, затем страница в кандидатах с причиной, остальные страницы обработаны",
         any("invalid_json" in c["reason"] for c in nl["candidates"]) and nl["status"] == "partial"
         and len(_events(res, event="retry", tool="extract_llm")) == 1, json.dumps(nl["candidates"], ensure_ascii=False)),
        ("недоступно всё и снимка нет → кандидат с причиной, задача не падает", lund["status"] == "partial"
         and lund["candidates"], json.dumps(lund["candidates"], ensure_ascii=False)[:160]),
        ("старое значение не потеряно и показывается со своей датой проверки",
         lund_card["deadline"]["working"]["date"] == "2026-02-16" and lund_card["deadline"]["working"]["checked_at"] == "2026-10-25",
         f"{lund_card['deadline']['working']['date']} checked {lund_card['deadline']['working']['checked_at']} status={lund_card['deadline']['status']}"),
    ]


def s2_cache_checks(res, agent):
    r = res.output["cached_recheck"]
    card = agent.nb.card("lund_global")
    return [
        ("сайт и запасной путь недоступны → последний снимок L0 (деградация)", r["status"] == "degraded"
         and r["pages"][0]["via"] == "last_snapshot", json.dumps(r["pages"], ensure_ascii=False)),
        ("дата проверки не «освежена» задним числом", card["deadline"]["working"]["checked_at"] == "2026-10-25",
         card["deadline"]["working"]["checked_at"]),
        ("значение старше 14 дней помечено «устарел»", card["deadline"]["status"] == "устарел", card["deadline"]["status"]),
    ]


# ---------- S3: упор в бюджет шагов ----------

S3_LEADS = ["Eiffel Excellence", "Chevening", "Gates Cambridge", "Knight-Hennessy", "Lund Global", "NL Scholarship",
            "Leiden Excellence", "Twente Scholarship", "Radboud Scholarship", "Maastricht High Potential",
            "ETH Excellence Scholarship", "Visegrad Scholarship"]


def s3_run(agent, ctx):
    return agent.discover_batch(ctx, S3_LEADS)


def s3_check(res, agent):
    p = res.output
    model_calls = len(_events(res, event="tool_call", tool="extract_llm"))
    with_facts = {r[0] for r in agent.nb.db.execute("SELECT DISTINCT scholarship_id FROM l1_facts")}
    with_cards = {c["scholarship_id"] for c in agent.nb.cards()}
    completed_ids = {d["scholarship_id"] for d in p.get("done", [])}
    return [
        ("остановка по бюджету, а не «крутится дальше»", res.status == BUDGET, f"{res.status}: {res.stop_reason}"),
        ("вызовов модели не больше бюджета шагов (10)", model_calls == res.usage["steps"] == 10, f"model_calls={model_calls}"),
        ("частичный результат: что сделано и что осталось", bool(p.get("done")) and bool(p.get("remaining")),
         f"done={len(p.get('done', []))} remaining={len(p.get('remaining', []))}"),
        ("нет «половины карточки»: у каждой стипендии с фактами есть карточка", with_facts <= with_cards,
         f"facts={sorted(with_facts)}"),
        ("незаконченная стипендия не записана в тетрадь", with_cards == completed_ids,
         f"cards={sorted(with_cards)} done={sorted(completed_ids)}"),
    ]


# ---------- S4: противоречие и изменение вводных ----------

S4_OVERRIDES = {"eiffel/agg_1.txt": {"dates": [_dl("2027-01-08", "2027/28", EIFFEL_AGG)], "amount": None},
                "eiffel/wb_1.txt": {"dates": [_dl("2023-01-10", "2022/23", EIFFEL_WB)], "amount": None}}


def s4_run(agent, ctx):
    steps = {}
    agent.ingest(ctx, "eiffel")
    steps["1_official"] = agent.answer_fact("eiffel")
    agent.ingest(ctx, "eiffel", pages=["eiffel/agg_1.txt"], source_type="aggregator")
    steps["2_aggregator"] = agent.answer_fact("eiffel")
    agent.ingest(ctx, "eiffel", pages=["eiffel/wb_1.txt"], source_type="past_snapshot")
    steps["3_wayback"] = agent.answer_fact("eiffel")
    c1, _ = agent.nb.user_correction("eiffel", "application_deadline", "2027-01-08", user="u1",
                                     note="«дедлайн 8 января, так на сайте-агрегаторе»")
    steps["4_user_later"] = agent.answer_fact("eiffel")
    agent.nb.undo_correction(c1, "пользователь: «я ошибся»")
    agent.nb.user_correction("eiffel", "application_deadline", "2027-01-05", user="u1",
                             note="«уточнил в Campus France: подача в моём вузе до 5 января»")
    steps["5_user_changed"] = agent.answer_fact("eiffel")
    return steps


def s4_check(res, agent):
    s = res.output
    all_facts = agent.nb.facts("eiffel", "application_deadline", active_only=False)
    return [
        ("официальный источник: 2027-01-06, подтверждён", s["1_official"]["value"] == "2027-01-06" and s["1_official"]["status"] == "подтверждён", str(s["1_official"])),
        ("агрегатор 8 января: официальное значение остаётся, статус «конфликт», оба показаны",
         s["2_aggregator"]["value"] == "2027-01-06" and s["2_aggregator"]["status"] == "конфликт"
         and ("2027-01-08", "aggregator") in s["2_aggregator"]["shown_alternatives"], str(s["2_aggregator"])),
        ("прошлогодний снимок 2023 не перебивает текущий цикл", s["3_wayback"]["value"] == "2027-01-06", str(s["3_wayback"]["shown_alternatives"])),
        ("пользователь называет более позднюю дату → рабочая остаётся ранней, конфликт виден",
         s["4_user_later"]["value"] == "2027-01-06" and s["4_user_later"]["status"] == "конфликт", str(s["4_user_later"])),
        ("вводные изменились (отмена + новая дата раньше официальной) → рабочая 2027-01-05, конфликт виден",
         s["5_user_changed"]["value"] == "2027-01-05" and s["5_user_changed"]["status"] == "конфликт"
         and ("2027-01-06", "official") in s["5_user_changed"]["shown_alternatives"], str(s["5_user_changed"])),
        ("ничего не затёрто: все значения остались в L1, отменённое — со статусом retracted",
         sorted(f["status"] for f in all_facts).count("retracted") == 1 and len(all_facts) == 5,
         str([(f["value"], f["source_type"], f["status"]) for f in all_facts])),
    ]


# ---------- S5: запись с повтором и отменой ----------

def s5_run(agent, ctx):
    out = {}
    agent.ingest(ctx, "nl_scholarship")
    out["before"] = agent.answer_fact("nl_scholarship")
    fid, created = agent.nb.user_correction("nl_scholarship", "application_deadline", "2027-02-01", user="u1",
                                            note="«на сайте вуза: подача на NL Scholarship до 1 февраля 2027»")
    fid2, created2 = agent.nb.user_correction("nl_scholarship", "application_deadline", "2027-02-01", user="u1",
                                              note="повтор после таймаута клиента")
    out["write"] = {"id": fid, "created": created, "retry_id": fid2, "retry_created": created2}
    out["control"] = [agent.answer_fact("nl_scholarship") for _ in range(5)]
    out["l3_after_write"] = agent.nb.summary_l3()
    agent.nb.undo_correction(fid)
    out["after_undo"] = agent.answer_fact("nl_scholarship")
    errs = []
    for action in (lambda: agent.nb.undo_correction(fid),
                   lambda: agent.nb.undo_correction(agent.nb.facts("nl_scholarship", "amount")[0]["id"]),
                   lambda: agent.nb.undo_correction(99999)):
        try:
            action()
            errs.append(None)
        except NotebookError as e:
            errs.append(e.code)
    out["undo_errors"] = errs
    return out


def s5_check(res, agent):
    o = res.output
    user_facts = agent.nb.facts("nl_scholarship", "application_deadline", active_only=False)
    user_facts = [f for f in user_facts if f["source_type"] == "user"]
    dup_events = [e for e in agent.nb.events() if e["action"] == "duplicate_ignored"]
    return [
        ("до исправления: дедлайна подачи на странице нет («не найдено»)", o["before"]["status"] == "не найдено", str(o["before"])),
        ("повтор той же записи идемпотентен: тот же id, дубля нет", o["write"]["id"] == o["write"]["retry_id"]
         and not o["write"]["retry_created"] and len(user_facts) == 1 and dup_events, str(o["write"])),
        ("5 контрольных вопросов после исправления его учитывают (M9)", all(c["value"] == "2027-02-01" and c["source"] == "user"
         for c in o["control"]), str([c["value"] for c in o["control"]])),
        ("исправление видно в L3", any(r["id"] == "nl_scholarship" for r in o["l3_after_write"]["nearest"]), ""),
        ("отмена возвращает состояние до исправления", o["after_undo"]["value"] is None and o["after_undo"]["status"] == "не найдено", str(o["after_undo"])),
        ("повторная отмена / отмена чужого факта / несуществующего — типизированные ошибки, состояние не меняется",
         o["undo_errors"] == ["already_retracted", "not_a_correction", "not_found"], str(o["undo_errors"])),
        ("след сохранён: исправление в L1 со статусом retracted", user_facts[0]["status"] == "retracted", user_facts[0]["status"]),
    ]


# ---------- S6: отравление памяти ----------

POISON_QUOTE = "The deadline to apply for the Lund University Global Scholarship is 16 February 2027."


def s6_run(agent, ctx):
    out = {}
    agent.ingest(ctx, "lund_global")
    out["clean"] = agent.answer_fact("lund_global")
    # 1) неверный факт записан в L1 в обход валидатора (как если бы баг или прямой доступ к базе)
    pid, _ = agent.nb.add_fact("lund_global", "application_deadline", "2027-02-16", source_type="official",
                               quote=POISON_QUOTE, page="lund_global/1.txt",
                               source_url="https://www.lunduniversity.lu.se/", checked_at="2026-10-25", cycle="2027/28")
    agent.nb.recompute("lund_global")
    out["poisoned_answer"] = agent.answer_fact("lund_global")
    out["poisoned_l3"] = any(r["id"] == "lund_global" for r in agent.nb.summary_l3()["nearest"])
    # 2) чистка: аудит L1 по L0
    out["quarantined"] = agent.nb.audit(norm)
    out["after_audit"] = agent.answer_fact("lund_global")
    out["after_audit_l3"] = any(r["id"] == "lund_global" and r["deadline"] == "2027-02-16"
                                for r in agent.nb.summary_l3()["nearest"])
    out["poison_id"] = pid
    # 3) тот же неверный факт через путь извлечения — валидатор не пускает его в L1
    #    (новая страница: у уже загруженных сработал бы кэш извлечения по sha256, модель бы не вызывалась)
    agent.extract.overrides["visegrad/1.txt"] = {"dates": [_dl("2027-05-31", "2027/28", "Applications close on 31 May 2027.")], "amount": None}
    out["ingest_poison"] = agent.ingest(ctx, "visegrad")
    out["visegrad"] = agent.answer_fact("visegrad")
    # 4) «отравление» через пользователя: более поздняя дата не становится рабочей
    agent.ingest(ctx, "eiffel")
    agent.nb.user_correction("eiffel", "application_deadline", "2027-03-01", user="u2", note="«дедлайн Eiffel 1 марта»")
    out["user_poison"] = agent.answer_fact("eiffel")
    return out


def s6_check(res, agent):
    o = res.output
    ev = agent.nb.events(o["poison_id"])
    return [
        ("неверный факт в L1 распространяется в L2 и L3 (так и должно быть: карточки — производные)",
         o["poisoned_answer"]["value"] == "2027-02-16" and o["poisoned_l3"], str(o["poisoned_answer"])),
        ("аудит по L0 находит его: цитаты нет в снимке → карантин", o["poison_id"] in o["quarantined"], str(o["quarantined"])),
        ("после чистки карточка и L3 вернулись к правде", o["after_audit"]["value"] == "2026-02-16"
         and o["after_audit"]["status"] == "устарел" and not o["after_audit_l3"], str(o["after_audit"])),
        ("след чистки в журнале", [e["action"] for e in ev] == ["insert", "quarantined"], str([(e["action"], e["reason"]) for e in ev])),
        ("через извлечение отравление не проходит: цитата не в снимке → отклонено валидатором",
         o["ingest_poison"]["rejected"] >= 1 and o["visegrad"]["value"] != "2027-05-31", f"rejected={o['ingest_poison']['rejected']} answer={o['visegrad']['value']}"),
        ("пользователь называет дату позже официальной → рабочая остаётся официальной", o["user_poison"]["value"] == "2027-01-06"
         and o["user_poison"]["status"] == "конфликт", str(o["user_poison"])),
    ]


# ---------- S7: длинный диалог и переполнение контекста ----------

def s7_run(agent, ctx):
    ids = ["chevening", "eiffel", "lund_global", "nl_scholarship", "gates_cambridge", "knight_hennessy",
           "leiden_excellence", "twente_uts", "radboud_scholarship", "maastricht_uhp", "eth_esop", "visegrad"]
    for sid in ids:
        agent.ingest(ctx, sid)
    session = "s7"
    for i in range(30):
        agent.nb.add_turn(session, "user", f"Вопрос {i}: какой дедлайн у стипендии номер {i} и подходит ли она мне? " + "подробности " * 25)
        agent.nb.add_turn(session, "assistant", f"Ответ {i}: дедлайн ..., источник ..., дата проверки ... " + "пояснение " * 30)
    agent.nb.set_summary(session, "Пользователь P1 (РФ, CS) спрашивал про дедлайны в ЕС; исправлений не было.", 40)
    turns = agent.nb.turns(session)
    profile = load_profile("P1")
    query = "Сравни Eiffel, Leiden, Twente, Radboud, Maastricht, ETH, Visegrad, Gates, Knight Hennessy и Lund по дедлайнам"
    cards = retrieve(agent.nb.cards(), query, _names())
    focus = agent.nb.facts("eiffel", "application_deadline")
    ctx_full = build_context("SYSTEM " * 1300, profile, agent.nb.summary_l3(), cards, turns,
                             agent.nb.summary(session)[0], focus)
    ctx_tight = build_context("SYSTEM " * 1300, profile, agent.nb.summary_l3(), cards, turns,
                              agent.nb.summary(session)[0], focus, budget={"cards": 1500, "history": 800, "l3": 400})
    return {"full": {k: v for k, v in ctx_full.items() if k != "parts"},
            "tight": {k: v for k, v in ctx_tight.items() if k != "parts"},
            "tight_has_system": ctx_tight["parts"]["system"].startswith("SYSTEM"),
            "tight_has_focus": "focus_l1" in ctx_tight["parts"], "retrieved": len(cards)}


def s7_check(res, agent):
    o = res.output
    t = o["tight"]
    return [
        ("контекст укладывается в 16k", o["full"]["total"] <= 16000 and t["total"] <= 16000, f"full={o['full']['total']} tight={t['total']}"),
        ("карточек не больше 8 из найденных", o["full"]["cards_in_context"] <= 8, f"retrieved={o['retrieved']} in={o['full']['cards_in_context']}"),
        ("история сверх своего бюджета: старые реплики → резюме, последние остаются", any(c.startswith("история") for c in t["cut"]), str(t["cut"][:3])),
        ("карточки сверх лимита/бюджета: выпадают наименее релевантные, у оставшихся режутся альтернативы", any(c.startswith("карточка") for c in t["cut"]), str([c for c in t["cut"] if c.startswith("карточка")][:3])),
        ("системный промпт, профиль и цитаты карточки в фокусе не режутся", o["tight_has_system"] and o["tight_has_focus"], ""),
    ]


SCENARIOS = [
    Scenario("S1", "Discovery: найти официальную страницу по названию, затем подстраницу с датами",
             "второй шаг зависит от результата первого", s1_run, s1_check),
    Scenario("S2", "Сбои инструментов посреди загрузки (5xx, 403, невалидный JSON, всё недоступно)",
             "ошибка инструмента посередине: ретрай / деградация / отказ", s2_run, s2_check, faults=S2_FAULTS),
    Scenario("S3", "«Найди и разбери 12 стипендий» при бюджете 10 шагов", "упор в бюджет шагов",
             s3_run, s3_check, budget={"max_steps": 10, "max_tool_calls": 200, "max_cost_usd": 1.0, "max_seconds": 120}),
    Scenario("S4", "Eiffel: агрегатор, прошлогодний снимок, пользователь меняет показания", "противоречие и изменение вводных",
             s4_run, s4_check, overrides=S4_OVERRIDES),
    Scenario("S5", "Исправление пользователя: повтор записи, 5 контрольных вопросов, отмена", "повтор и отмена записи",
             s5_run, s5_check),
    Scenario("S6", "Отравление памяти: неверный факт в L1, через извлечение и через пользователя", "тест на отравление памяти",
             s6_run, s6_check),
    Scenario("S7", "Длинный диалог (60 реплик) и 12 карточек: сборка контекста под бюджет", "переполнение контекста",
             s7_run, s7_check, budget={"max_steps": 60, "max_tool_calls": 200, "max_cost_usd": 1.0, "max_seconds": 120}),
]


# Лимиты инструментов в контракте — на одну стипендию; сценарий обрабатывает до 12, поэтому лимиты шире,
# а ограничивает его бюджет шагов (S3 проверяет именно это).
SCENARIO_TOOL_LIMITS = {"fetch": 60, "fetch_alt": 20, "list_pages": 20, "extract_llm": 60, "search": 20}


class ScenarioSystem:
    name = "agent-replay"

    def __init__(self):
        self.agents: dict[str, NotebookAgent] = {}

    def config(self) -> dict:
        return {"extractor": ReplayExtractor.prompt_sha, "model": None, "temperature": None,
                "seed": None, "notebook": "sqlite :memory:, свежая на каждый сценарий"}

    def run(self, task: Task, ctx: Context):
        sc: Scenario = task.input["scenario"]
        agent = NotebookAgent(Notebook(), ReplayExtractor(dict(sc.overrides or {})))
        self.agents[task.id] = agent
        return OK, sc.run(agent, ctx)


def run_scenarios(only: str | None) -> None:
    requested = set(only.split(",")) if only else {s.id for s in SCENARIOS}
    unknown = requested - {s.id for s in SCENARIOS}
    if unknown:
        raise SystemExit(f"неизвестные сценарии: {', '.join(sorted(unknown))}")
    chosen = [s for s in SCENARIOS if s.id in requested]
    system = ScenarioSystem()
    tasks = [Task(s.id, "scenario", {"scenario": s, "tool_limits": SCENARIO_TOOL_LIMITS,
                                     **({"budget": s.budget} if s.budget else {}),
                                     **({"faults": s.faults} if s.faults else {})}) for s in chosen]
    started, t0 = now()
    budget = Budget(max_steps=40, max_tool_calls=200, max_cost_usd=0.5)
    results = run_tasks(system, tasks, budget)
    per, passed_all = [], 0
    for s, r in zip(chosen, results):
        try:
            checks = s.check(r, system.agents[s.id])
        except Exception as e:      # проверка упала — это провал сценария, а не харнесса
            checks = [("проверка выполнима", False, f"{type(e).__name__}: {e}; status={r.status} {r.stop_reason}")]
        ok = all(c[1] for c in checks)
        passed_all += ok
        per.append({"id": s.id, "title": s.title, "requirement": s.requirement, "status": r.status,
                    "stop_reason": r.stop_reason, "passed": ok, "usage": r.usage,
                    "checks": [{"name": n, "ok": bool(v), "detail": d} for n, v, d in checks]})
        print(f"\n{s.id} [{'PASS' if ok else 'FAIL'}] {s.title}  ({r.status}, steps={r.usage['steps']}, "
              f"tools={r.usage['tool_calls']}, ${r.usage['cost_usd']}, {r.usage['seconds']}s)")
        for n, v, d in checks:
            print(f"   {'✓' if v else '✗'} {n}" + (f"  — {d}" if not v else ""))
    for r in results:   # сценарий в output не сериализуем — только результат
        r.output = json.loads(json.dumps(r.output, ensure_ascii=False, default=str))
    metrics = {"scenarios": len(chosen), "passed": passed_all,
               "checks": sum(len(x["checks"]) for x in per), "checks_passed": sum(c["ok"] for x in per for c in x["checks"])}
    out = save_run(system, "scenarios", budget, results, metrics, per, started, time.perf_counter() - t0,
                   "многошаговые сценарии", tasks=tasks)
    print(f"\n{passed_all}/{len(chosen)} сценариев, {metrics['checks_passed']}/{metrics['checks']} проверок → {out}")

    if passed_all != len(chosen):
        raise SystemExit(1)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--only")
    run_scenarios(parser.parse_args().only)


if __name__ == "__main__":
    main()
