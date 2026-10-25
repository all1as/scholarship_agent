"""Разбиение A2 на видимую (70) и отложенную (30) части (design doc, раздел 7.5).

Единица разбиения — стипендия. Подвыборка для согласия разметчиков (включает стипендии спайка) — всегда видимая.
Остальные стратифицируются по стране и по наличию ловушек; порядок внутри страты — по sha256(id), без случайности.
Выход: eval/gt/split.csv (id, part), eval/gt/labels_heldout.jsonl (локально, в git не попадает — шифруется heldout.py),
eval/gt/labels_a.jsonl остаётся только с видимыми метками.
"""

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GT = ROOT / "eval" / "gt"
HELDOUT_N = 30


def main() -> None:
    labels = {l["id"]: l for l in map(json.loads, (GT / "labels_a.jsonl").read_text(encoding="utf-8").splitlines()) if l}
    country = {r["id"]: r["country"] for r in csv.DictReader((GT / "reference_list.csv").open(encoding="utf-8"))}
    forced = set((GT / "agreement_subset.txt").read_text(encoding="utf-8").split())
    pool = [i for i in labels if i not in forced]

    strata = defaultdict(list)
    for i in pool:
        has_trap = "trap" if labels[i]["traps"] else "plain"
        strata[(country[i], has_trap)].append(i)
    for key in strata:
        strata[key].sort(key=lambda i: hashlib.sha256(i.encode()).hexdigest())

    # пропорциональное распределение 30 мест по стратам (метод наибольших остатков)
    quotas = {k: HELDOUT_N * len(v) / len(pool) for k, v in strata.items()}
    take = {k: int(q) for k, q in quotas.items()}
    for k in sorted(quotas, key=lambda k: quotas[k] - take[k], reverse=True)[: HELDOUT_N - sum(take.values())]:
        take[k] += 1
    heldout = {i for k, ids in strata.items() for i in ids[: take[k]]}

    with (GT / "split.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "part"])
        for i in sorted(labels):
            w.writerow([i, "heldout" if i in heldout else "visible"])
    (GT / "labels_heldout.jsonl").write_text(
        "".join(json.dumps(labels[i], ensure_ascii=False) + "\n" for i in sorted(heldout)), encoding="utf-8")
    (GT / "labels_a.jsonl").write_text(
        "".join(json.dumps(labels[i], ensure_ascii=False) + "\n" for i in labels if i not in heldout), encoding="utf-8")
    print(f"видимых: {len(labels) - len(heldout)}, отложенных: {len(heldout)}")


if __name__ == "__main__":
    main()
