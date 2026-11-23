"""Сборка контекста на один шаг ответа (design doc, раздел 6): что попадает в промпт, в каком порядке и что режется.

Бюджет входа на ответ — 16k токенов (раздел 3.1):
  системный промпт + описания инструментов 2,5k | профиль 0,5k | L3 ≤3k | карточки L2 ≤6,5k | история ≤3k | резерв 0,5k
У каждого блока свой потолок, поэтому переполнение одного блока не вытесняет другие. Что режется внутри блока:
  - история: старые реплики сворачиваются в резюме, в контексте остаются последние, сколько влезает
    (режется легче всего: резюме и тетрадь хранят суть, а факты всё равно берутся из L2, а не из истории);
  - карточки: не больше 8; сначала у менее релевантных отрезаются альтернативные значения (рабочее значение,
    статус и источник остаются), затем наименее релевантные выпадают целиком;
  - L3: обрезается до ближайших дедлайнов и блока «требует внимания»;
  - никогда не режутся: системный промпт, профиль, факты с цитатами для карточки в фокусе (провенанс обязателен).
    Если системный промпт или профиль не влезают в свой потолок — это ошибка конфигурации, сборка падает.
L1 (цитаты) попадает в контекст только для карточки в фокусе вопроса (источник, конфликт, исправление).
"""

from __future__ import annotations

import json
import re

BUDGET = {"system": 2500, "profile": 500, "l3": 3000, "cards": 6500, "history": 3000, "reserve": 500}
TOTAL = 16000
MAX_CARDS = 8


def tokens(text: str) -> int:
    """Оценка без токенизатора провайдера: ~4 символа на токен для смешанного RU/EN JSON.
    Для отчёта о стоимости используются реальные usage от API; здесь — только для раскладки бюджета."""
    return (len(text) + 3) // 4


def _dump(x) -> str:
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"))


def retrieve(cards: list[dict], query: str, names: dict[str, list[str]]) -> list[tuple[float, dict]]:
    q = set(re.findall(r"[a-zа-я0-9]+", query.lower()))
    scored = []
    for c in cards:
        words = set(re.findall(r"[a-z0-9]+", " ".join(names.get(c["scholarship_id"], [c["scholarship_id"]])).lower()))
        words |= set(c["scholarship_id"].split("_"))
        score = len(q & words) + (0.5 if c["deadline"]["status"] in ("конфликт", "устарел") else 0)
        if score:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    return scored


def build_context(system_prompt: str, profile: dict, l3: dict, cards: list[tuple[float, dict]],
                  history: list[dict], summary: str, focus_facts: list[dict] | None = None,
                  budget: dict | None = None) -> dict:
    b = {**BUDGET, **(budget or {})}
    cut: list[str] = []
    parts: dict[str, str] = {"system": system_prompt, "profile": _dump(profile)}
    if tokens(parts["system"]) > b["system"] or tokens(parts["profile"]) > b["profile"]:
        raise ValueError("системный промпт или профиль больше своего бюджета — это ошибка конфигурации, а не данных")

    # L3: целиком или только ближайшие + внимание
    l3_text = _dump(l3)
    if tokens(l3_text) > b["l3"]:
        slim = {"today": l3["today"], "attention": list(l3["attention"]), "nearest": list(l3["nearest"])}
        while tokens(_dump(slim)) > b["l3"] and (slim["nearest"] or slim["attention"]):
            (slim["nearest"] if len(slim["nearest"]) >= len(slim["attention"]) else slim["attention"]).pop()
        l3_text = _dump(slim)
        if tokens(l3_text) > b["l3"]:
            l3_text = ""
        cut.append("l3: обрезан до ближайших дедлайнов и блока внимания")
    parts["l3"] = l3_text

    # карточки: по релевантности, до MAX_CARDS и бюджета
    kept = []
    focus_text = _dump(focus_facts) if focus_facts else ""
    budget_cards = b["cards"] - tokens(focus_text)
    if budget_cards < tokens("[]"):
        raise ValueError("факты с цитатами в фокусе превышают бюджет карточек")
    def card_tokens(candidate: str) -> int:
        return tokens("[" + ",".join([*kept, candidate]) + "]")

    for i, (score, c) in enumerate(cards[:MAX_CARDS]):
        t = _dump(c)
        if card_tokens(t) > budget_cards:
            slim = {**c, "deadline": {**c["deadline"], "alternatives": [] if i else c["deadline"]["alternatives"][:2]},
                    "amount": {**c["amount"], "alternatives": []}}
            t = _dump(slim)
            cut.append(f"карточка {c['scholarship_id']}: альтернативные значения отрезаны")
        if card_tokens(t) > budget_cards:
            cut.append(f"карточка {c['scholarship_id']}: не влезла (релевантность {score})")
            continue
        kept.append(t)
    for score, c in cards[MAX_CARDS:]:
        cut.append(f"карточка {c['scholarship_id']}: сверх лимита {MAX_CARDS} карточек")
    parts["cards"] = "[" + ",".join(kept) + "]"
    if focus_text:
        parts["focus_l1"] = focus_text

    # история: последние реплики, остальное — в резюме
    hist = []
    prefix = "Резюме ранее: " + summary + "\n" if summary else ""
    if tokens(prefix) > b["history"]:
        cut.append("история: резюме сокращено до бюджета")
        prefix = prefix[:4 * b["history"]]
    for turn in reversed(history):
        t = f"{turn['role']}: {turn['text']}"
        if tokens(prefix + "\n".join([t, *hist])) > b["history"]:
            cut.append(f"история: реплики до №{turn['turn']} исключены из контекста")
            break
        hist.insert(0, t)
    parts["history"] = prefix + "\n".join(hist)

    sizes = {k: tokens(v) for k, v in parts.items()}
    total = sum(sizes.values())
    if total > TOTAL:
        raise ValueError(f"контекст {total} > {TOTAL}")
    return {"parts": parts, "tokens": sizes, "total": total, "cut": cut,
            "cards_in_context": len(kept), "history_turns": len(hist)}
