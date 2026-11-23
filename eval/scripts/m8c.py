"""M8(в): подтверждает ли цитата именно это значение, тип даты, цикл и область (design doc 3.1).

M8(а) проверяет только, что цитата есть в снимке. Настоящую цитату можно приклеить к неверной дате или
неверной области — это ловит M8(в): на случайной выборке фактов из прогона проверяющий (LLM-агент другой
модели, чем экстрактор; инструкция — docs/m8c_checker_prompt.md) отвечает по каждому полю «да / нет».

    python eval/scripts/m8c.py sample runs/<id> [--n 30] [--seed 2027]   → runs/<id>/m8c_sample.jsonl
    (проверяющий пишет runs/<id>/m8c_verdicts.jsonl: {"fid", "value_ok", "type_ok", "cycle_ok", "scope_ok", "comment"})
    python eval/scripts/m8c.py score runs/<id>                            → runs/<id>/m8c.json
"""

import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIELDS = ("value_ok", "type_ok", "cycle_ok", "scope_ok")


def facts(run: Path) -> list[dict]:
    out = []
    for line in (run / "results.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        o = r.get("output") or {}
        for d in o.get("application_deadlines") or []:
            out.append({"kind": "deadline", "scholarship_id": r["task_id"], "claimed_type": "application",
                        **{k: d.get(k) for k in ("date", "granularity", "cycle", "scope", "scope_detail", "quote", "page")}})
        a = o.get("amount")
        if a:
            out.append({"kind": "amount", "scholarship_id": r["task_id"],
                        **{k: a.get(k) for k in ("value", "currency", "period", "full_coverage", "quote", "page")}})
    return out


def sample(run: Path, n: int, seed: int) -> None:
    fs = facts(run)
    rng = random.Random(seed)
    dl = [f for f in fs if f["kind"] == "deadline"]
    am = [f for f in fs if f["kind"] == "amount"]
    k_dl = min(len(dl), round(n * 2 / 3))
    picked = rng.sample(dl, k_dl) + rng.sample(am, min(len(am), n - k_dl))
    with (run / "m8c_sample.jsonl").open("w", encoding="utf-8") as fh:
        for i, f in enumerate(picked, 1):
            fh.write(json.dumps({"fid": f"f{i:02d}", **f, "snapshot": f"eval/gt/pages/{f['page']}"}, ensure_ascii=False) + "\n")
    print(f"{len(picked)} фактов из {len(fs)} (сроки {k_dl}, суммы {len(picked) - k_dl}) → {run / 'm8c_sample.jsonl'}")


def score(run: Path) -> None:
    sample_ = {json.loads(l)["fid"]: json.loads(l) for l in (run / "m8c_sample.jsonl").read_text(encoding="utf-8").splitlines() if l}
    verdicts = [json.loads(l) for l in (run / "m8c_verdicts.jsonl").read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    assert {v["fid"] for v in verdicts} == set(sample_), "вердикты не по всей выборке"
    applicable = lambda v, f: v.get(f) is not None   # null — поле к факту не применимо (у суммы нет цикла)
    res = {"n": len(verdicts), "supported": sum(all(v[f] is not False for f in FIELDS) for v in verdicts)}
    res["M8c"] = round(res["supported"] / res["n"], 3)
    res["by_field"] = {f: f"{sum(v[f] is True for v in verdicts)}/{sum(applicable(v, f) for v in verdicts)}" for f in FIELDS}
    res["failures"] = [{**v, "fact": {k: sample_[v["fid"]].get(k) for k in ("scholarship_id", "kind", "date", "value", "scope", "cycle", "quote")}}
                       for v in verdicts if any(v[f] is False for f in FIELDS)]
    (run / "m8c.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("n", "supported", "M8c", "by_field")}, ensure_ascii=False))


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("run")
    s.add_argument("--n", type=int, default=30)
    s.add_argument("--seed", type=int, default=2027)
    sc = sub.add_parser("score")
    sc.add_argument("run")
    a = p.parse_args()
    run = Path(a.run) if Path(a.run).is_absolute() else ROOT / a.run
    sample(run, a.n, a.seed) if a.cmd == "sample" else score(run)


if __name__ == "__main__":
    main()
