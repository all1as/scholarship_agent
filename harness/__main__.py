"""CLI харнесса.

  python -m harness run --system b1 --suite extract            # B1 на видимой части A2
  python -m harness run --system llm --suite extract --limit 5 # LLM-извлечение (нужен ключ в .env)
  python -m harness compare runs/<id1> runs/<id2>              # таблица метрик, стоимости и времени
  python -m harness contracts                                  # контракты инструментов (для раздела 5)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import Budget
from .metrics import score_extract
from .scenarios import run_scenarios
from .runner import extract_tasks, now, run_tasks, save_run
from .systems import get_system
from .tools import contracts_markdown

COMPARE_KEYS = ["M4", "M4_ci95", "M4_with_dates", "M4_no_dates", "M4_status_acc", "M4_set_acc",
                "M4_dangerous_per_100", "M4_dangerous_by_type", "M5", "M5_on_stated",
                "M6", "M8a", "facts"]


def cmd_run(a: argparse.Namespace) -> None:
    import time
    system = get_system(a.system, **({"model": a.model} if a.model else {}))
    budget = Budget(max_steps=a.max_steps, max_cost_usd=a.max_cost)
    tasks, labels = extract_tasks(a.ids.split(",") if a.ids else None)
    tasks = tasks[: a.limit] if a.limit else tasks
    started, t0 = now()
    results = run_tasks(system, tasks, budget)
    per_task, metrics = score_extract(results, labels)
    out = save_run(system, a.suite, budget, results, metrics, per_task, started, time.perf_counter() - t0, a.note, tasks=tasks)
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    print(json.dumps({"run": str(out.relative_to(Path.cwd())) if out.is_relative_to(Path.cwd()) else str(out),
                      "metrics": metrics, "totals": meta["totals"]}, ensure_ascii=False, indent=2))


def cmd_compare(a: argparse.Namespace) -> None:
    runs = [Path(p) for p in a.runs]
    metas = [json.loads((r / "meta.json").read_text(encoding="utf-8")) for r in runs]
    reference = metas[0]
    for meta in metas[1:]:
        for key in ("suite", "eval_set", "task_ids", "budget_per_task", "task_overrides", "tool_contracts"):
            if key not in reference or key not in meta or reference[key] != meta[key]:
                raise SystemExit(f"прогоны несопоставимы: {key}")
    mets = [json.loads((r / "metrics.json").read_text(encoding="utf-8")) for r in runs]
    head = ["метрика"] + [f"{m['system']['name']} ({m['system'].get('model') or 'rules'})" for m in metas]
    rows = [head, ["---"] * len(head)]
    for k in COMPARE_KEYS:
        rows.append([k] + [str(m.get(k)) for m in mets])
    for k in ["cost_usd", "tokens_in", "tokens_out", "wall_seconds", "task_seconds_p50", "task_seconds_p95"]:
        rows.append([k] + [str(m["totals"][k]) for m in metas])
    rows.append(["eval"] + [f"{m['eval_set']['version']} {m['eval_set']['sha256']['labels_a.jsonl']}" for m in metas])
    rows.append(["commit"] + [m["git"]["commit"][:8] + ("*" if m["git"]["dirty"] else "") for m in metas])
    print("\n".join("| " + " | ".join(r) + " |" for r in rows))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="harness")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--system", required=True)
    r.add_argument("--suite", default="extract", choices=["extract"])
    r.add_argument("--model")
    r.add_argument("--ids")
    r.add_argument("--limit", type=int)
    r.add_argument("--max-steps", type=int, default=8)
    r.add_argument("--max-cost", type=float, default=0.05)
    r.add_argument("--note", default="")
    scenarios = sub.add_parser("scenarios")
    scenarios.add_argument("--only")
    c = sub.add_parser("compare")
    c.add_argument("runs", nargs="+")
    sub.add_parser("contracts")
    a = p.parse_args()
    {"run": cmd_run, "scenarios": lambda args: run_scenarios(args.only),
     "compare": cmd_compare, "contracts": lambda _: print(contracts_markdown())}[a.cmd](a)


if __name__ == "__main__":
    main()
