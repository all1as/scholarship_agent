"""Сборка части B и деление на видимую и отложенную части (design doc, разделы 7.3 и 7.5).

- Запрос, затрагивающий хотя бы одну отложенную стипендию (eval/gt/split.csv), — в отложенную часть.
- Остальные добираются до ~30 % в каждой категории детерминированно (порядок по sha256(id)).
- Видимая часть: eval/queries/visible.jsonl. Отложенная: eval/gt/heldout_bundle.jsonl (локально, не в git)
  вместе с отложенными метками A2 и парами A4 (eval/gt/duplicates_heldout.jsonl); затем шифруется heldout.py.
"""

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GT, Q = ROOT / "eval" / "gt", ROOT / "eval" / "queries"
EVAL_DATE = "2026-10-25"
SHARE = 0.3


def main() -> None:
    queries = json.loads((Q / "queries_draft.json").read_text(encoding="utf-8"))
    held_ids = {r["id"] for r in csv.DictReader((GT / "split.csv").open(encoding="utf-8")) if r["part"] == "heldout"}
    by_cat = defaultdict(list)
    for q in queries:
        q["eval_date"] = EVAL_DATE
        q["split"] = "heldout" if set(q["scholarship_ids"]) & held_ids else None
        by_cat[q["category"]].append(q)
    for cat, items in by_cat.items():
        need = round(SHARE * len(items)) - sum(q["split"] == "heldout" for q in items)
        free = sorted((q for q in items if q["split"] is None), key=lambda q: hashlib.sha256(q["id"].encode()).hexdigest())
        for q in free[:max(need, 0)]:
            q["split"] = "heldout"
        for q in items:
            q["split"] = q["split"] or "visible"

    visible = [q for q in queries if q["split"] == "visible"]
    heldout = [q for q in queries if q["split"] == "heldout"]
    (Q / "visible.jsonl").write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in visible), encoding="utf-8")
    labels = [json.loads(l) for l in (GT / "labels_heldout.jsonl").read_text(encoding="utf-8").splitlines() if l]
    dups_path = GT / "duplicates_heldout.jsonl"
    dups = [json.loads(l) for l in dups_path.read_text(encoding="utf-8").splitlines() if l] if dups_path.exists() else []
    bundle = ([{"kind": "label", "data": l} for l in labels] + [{"kind": "query", "data": q} for q in heldout]
              + [{"kind": "duplicate", "data": d} for d in dups])
    (GT / "heldout_bundle.jsonl").write_text("".join(json.dumps(b, ensure_ascii=False) + "\n" for b in bundle), encoding="utf-8")
    print(f"запросов: {len(queries)}; видимых: {len(visible)}; отложенных: {len(heldout)}")
    for cat, items in by_cat.items():
        print(f"  {cat:<18} всего {len(items):<3} отложено {sum(q['split'] == 'heldout' for q in items)}")


if __name__ == "__main__":
    main()
