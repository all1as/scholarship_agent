"""Согласие разметчиков A и B на подвыборке (design doc, раздел 7.4).

- дедлайны подачи: совпадение множеств (дата, точность, область) по стипендии;
- статус цикла и open_to_ru: κ Коэна;
- основная выплата: совпадение (сумма, валюта, период, полное покрытие).
Запуск: python eval/scripts/agreement.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GT = ROOT / "eval" / "gt"


def load(name: str) -> dict[str, dict]:
    labels = (json.loads(line) for line in (GT / name).read_text(encoding="utf-8-sig").splitlines() if line.strip())
    return {label["id"]: label for label in labels}


def deadlines(label: dict) -> set[tuple]:
    return {(d["date"], d["granularity"], d["scope"]) for d in label["application_deadlines"]}


def amount(label: dict) -> tuple | None:
    a = label["amount"]
    return None if a is None else (a["value"], a["currency"], a["period"], a["full_coverage"])


def cohen_kappa(pairs: list[tuple[str, str]]) -> float:
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(ca[k] * cb[k] for k in ca.keys() | cb.keys()) / n ** 2
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    subset = [s.strip() for s in (GT / "agreement_subset.txt").read_text(encoding="utf-8").split() if s.strip()]
    a, b = load("labels_a.jsonl"), load("labels_b.jsonl")
    missing = [s for s in subset if s not in a or s not in b]
    if missing:
        print("нет метки у A или B:", ", ".join(missing))
    ids = [s for s in subset if s in a and s in b]

    dl = [deadlines(a[i]) == deadlines(b[i]) for i in ids]
    am = [amount(a[i]) == amount(b[i]) for i in ids]
    status = [(a[i]["cycle_status"], b[i]["cycle_status"]) for i in ids]
    ru = [(a[i]["open_to_ru"]["value"], b[i]["open_to_ru"]["value"]) for i in ids]

    print(f"стипендий: {len(ids)}")
    print(f"дедлайны подачи (дата + точность + область), полное совпадение: {sum(dl)}/{len(ids)} = {sum(dl) / len(ids):.0%}  (цель ≥90 %)")
    print(f"основная выплата, совпадение: {sum(am)}/{len(ids)} = {sum(am) / len(ids):.0%}  (цель ≥85 %)")
    print(f"статус цикла: κ = {cohen_kappa(status):.2f}  (цель ≥0,8)")
    print(f"open_to_ru: κ = {cohen_kappa(ru):.2f}  (цель ≥0,8)")

    print("\nРасхождения (для проверки человеком):")
    for i, d_ok, a_ok, (sa, sb), (ra, rb) in zip(ids, dl, am, status, ru):
        if d_ok and a_ok and sa == sb and ra == rb:
            continue
        print(f"- {i}")
        if not d_ok:
            print(f"    дедлайны A: {sorted(deadlines(a[i]))}\n    дедлайны B: {sorted(deadlines(b[i]))}")
        if not a_ok:
            print(f"    выплата A: {amount(a[i])}  B: {amount(b[i])}")
        if sa != sb:
            print(f"    статус A: {sa}  B: {sb}")
        if ra != rb:
            print(f"    open_to_ru A: {ra}  B: {rb}")


if __name__ == "__main__":
    main()
