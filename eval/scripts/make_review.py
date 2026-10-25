"""Читаемые файлы для проверки человеком (design doc, раздел 7.4).

- eval/review/labels_check.md — 20 случайных видимых меток A2 + 6 расхождений с разметчиком B;
  по каждому полю: значение, цитата, ссылка на снимок и колонка для отметки.
- eval/review/queries_b.md — видимые запросы части B по категориям.
Выборка детерминирована (seed), чтобы проверяющий и автор видели одно и то же.
"""

import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GT, OUT = ROOT / "eval" / "gt", ROOT / "eval" / "review"
SEED, N = 2027, 20
DISPUTED = ["eiffel", "boell_international", "kas_international", "commonwealth_masters", "master_mind",
            "dk_government_scholarship_au"]
CATEGORY_RU = {
    "fact_deadline": "Факт: дедлайн", "fact_amount": "Факт: сумма и покрытие", "requirements": "Требования",
    "discovery": "Поиск стипендий (discovery)", "time": "Время: ближайшие и закрывшиеся",
    "stale_cycle": "Устаревший цикл", "conflict": "Конфликт источников", "provenance": "Источник и цитата",
    "boundary": "Граница контракта", "correction_memory": "Исправления и память (многоходовые)",
    "nonexistent": "Несуществующие стипендии", "out_of_domain": "Вне домена и prompt injection",
}


def link(page: str | None) -> str:
    return f"[{page}](../gt/pages/{page})" if page else "—"


def cell(text) -> str:
    return "—" if text in (None, "", []) else str(text).replace("|", "\\|").replace("\n", " ")


def yn(v) -> str:
    return {True: "да", False: "нет", None: "не сказано"}.get(v, str(v))


def label_rows(l: dict) -> list[tuple]:
    rows = [("уровень", ", ".join(l["levels"]["value"]) or "не указан", l["levels"]["quote"], l["levels"]["page"]),
            ("статус цикла 2027/28", l["cycle_status"], None, None)]
    for d in l["application_deadlines"]:
        value = f"{d['date']} ({d['granularity']}), цикл {d['cycle']}, область {d['scope']}" + (
            f" — {d['scope_detail']}" if d["scope_detail"] else "")
        rows.append(("дедлайн подачи", value, d["quote"], d["page"]))
    for d in l["other_dates"]:
        rows.append((f"другая дата: {d['type']}", f"{d['date']} ({d['granularity']})", d["quote"], d["page"]))
    a = l["amount"]
    if a:
        amount = f"{a['value']} {a['currency']} / {a['period']}" if a["value"] is not None else "сумма не указана"
        value = f"{amount}; полное покрытие: {yn(a['full_coverage'])}" + (
            f"; варианты: {a['variants']}" if a["variants"] else "")
        rows.append(("сумма", value, a["quote"], a["page"]))
    else:
        rows.append(("сумма", "нет на странице", None, None))
    c = l["covers"]
    rows.append(("покрывает", f"обучение: {yn(c['tuition'])}, проживание: {yn(c['living'])}, перелёт: {yn(c['travel'])}",
                 c["quote"], c["page"]))
    o = l["open_to_ru"]
    rows.append(("открыта для РФ", o["value"], o["quote"], o["page"]))
    return rows


def labels_md(labels: dict) -> str:
    rng = random.Random(SEED)
    sample = sorted(rng.sample(sorted(i for i in labels if i not in DISPUTED), N))
    out = ["# Проверка меток A2 человеком", "",
           "Как проверять: открыть файл снимка по ссылке, найти цитату поиском (Ctrl+F) и решить, следует ли значение из цитаты. "
           "Знание предметной области не нужно. В колонку «✔/✘» поставить ✔ или ✘; при ✘ — записать в `eval/gt/adjudication.md`: "
           "id, поле, было, стало, почему.", "",
           f"Выборка: {N} случайных видимых меток (seed {SEED}) + {len(DISPUTED)} стипендий, где расходились разметчики A и B.", ""]
    for title, ids in (("Случайная выборка", sample), ("Расхождения A и B (решение уже принято — проверить, согласен ли)", DISPUTED)):
        out += [f"## {title}", ""]
        for i in ids:
            l = labels[i]
            out += [f"### {l['name']} (`{i}`)", "", f"Примечание разметчика: {cell(l['notes'])}", "",
                    "| Поле | Значение | Цитата | Снимок | ✔/✘ |", "|---|---|---|---|---|"]
            out += [f"| {f} | {cell(v)} | {cell(q)} | {link(p)} | |" for f, v, q, p in label_rows(l)]
            out.append("")
    return "\n".join(out)


def queries_md(queries: list[dict], labels: dict) -> str:
    by_cat = defaultdict(list)
    for q in queries:
        by_cat[q["category"]].append(q)
    out = ["# Часть B: видимые запросы", "",
           f"Всего {len(queries)} видимых запросов (отложенные зашифрованы). Дата eval — 25.10.2026. "
           "Профили: P1 — гражданин РФ, CS/DS/ML, ЕС/UK/Швейцария; P2 — гражданин РФ, инженерия/embedded, США/Канада/Германия/Скандинавия.", "",
           "Для переформулировки человеком (обещано в design doc, 7.3): выбрать 20 запросов, переписать текст в колонке «Запрос» своими словами "
           "и прислать список «id → новый текст».", ""]
    for cat, items in by_cat.items():
        out += [f"## {CATEGORY_RU.get(cat, cat)} ({len(items)})", "",
                "| id | Профиль | Запрос | Ожидается | Обязательно | Недопустимо | Стипендии |", "|---|---|---|---|---|---|---|"]
        for q in items:
            turns = " → ".join(f"«{t}»" for t in q["turns"])
            names = ", ".join(labels[i]["name"] if i in labels else i for i in q["scholarship_ids"])
            out.append(f"| {q['id']} | {q['profile'] or '—'} | {cell(turns)} | {q['expected']['behavior']} | "
                       f"{cell('; '.join(q['expected']['must']))} | {cell('; '.join(q['expected']['must_not']))} | {cell(names)} |")
        out.append("")
    return "\n".join(out)


def main() -> None:
    labels = {l["id"]: l for l in map(json.loads, (GT / "labels_a.jsonl").read_text(encoding="utf-8").splitlines()) if l}
    queries = [json.loads(l) for l in (ROOT / "eval" / "queries" / "visible.jsonl").read_text(encoding="utf-8").splitlines() if l]
    OUT.mkdir(exist_ok=True)
    (OUT / "labels_check.md").write_text(labels_md(labels), encoding="utf-8")
    (OUT / "queries_b.md").write_text(queries_md(queries, labels), encoding="utf-8")
    print("готово:", OUT / "labels_check.md", OUT / "queries_b.md")


if __name__ == "__main__":
    main()
