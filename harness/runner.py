"""Раннер: один и тот же код прогоняет любую систему на наборе и сохраняет результат вместе с метаданными."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .core import BUDGET, ERROR, Budget, BudgetExceeded, Context, Meter, Result, System, Task
from .tools import CONTRACTS, EVAL_DATE, ROOT, ToolError, Toolbox

EVAL_VERSION = "v1"
RUNS = ROOT / "runs"
GT = ROOT / "eval" / "gt"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def visible_ids() -> set[str]:
    with open(GT / "split.csv", encoding="utf-8-sig") as f:
        return {r["id"] for r in csv.DictReader(f) if r["part"] == "visible"}


def load_labels() -> dict[str, dict]:
    vis = visible_ids()
    labels = {}
    for line in (GT / "labels_a.jsonl").read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            lab = json.loads(line)
            assert lab["id"] in vis, f"{lab['id']}: метка не из видимой части — отложенная часть до КТ4 не используется"
            labels[lab["id"]] = lab
    return labels


def extract_tasks(ids: list[str] | None = None) -> tuple[list[Task], dict[str, dict]]:
    labels = load_labels()
    chosen = ids or sorted(labels)
    return [Task(i, "extract", {"scholarship_id": i, "name": labels[i]["name"]}, labels[i]) for i in chosen], labels


def git_state() -> dict:
    def git(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        except Exception:
            return ""
    return {"commit": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(git("status", "--porcelain", "--", "harness", "eval"))}


def eval_fingerprint() -> dict:
    files = ["labels_a.jsonl", "split.csv", "pages/manifest.csv", "conflicts.jsonl",
             "duplicates.jsonl", "reference_list.csv"]
    snapshots = {str(p.relative_to(GT).as_posix()): sha256_file(p)
                 for sid in sorted(visible_ids()) for p in sorted((GT / "pages" / sid).glob("*.txt"))}
    return {"version": EVAL_VERSION, "part": "visible", "clock": EVAL_DATE,
            "visible_snapshots_sha256": hashlib.sha256(json.dumps(snapshots, sort_keys=True).encode()).hexdigest(),
            "sha256": {f: sha256_file(GT / f) for f in files}}


def run_tasks(system: System, tasks: list[Task], budget: Budget, faults: dict | None = None) -> list[Result]:
    allowed = visible_ids()
    results = []
    for task in tasks:
        meter = Meter(Budget(**task.input["budget"]) if "budget" in task.input else budget)
        holder: dict = {}
        ctx = Context(tools=Toolbox(lambda: holder["ctx"], faults=(faults or {}).get(task.id) or task.input.get("faults"),
                                    allowed_ids=allowed, limits=task.input.get("tool_limits")), meter=meter)
        holder["ctx"] = ctx
        stop = None
        try:
            status, output = system.run(Task(task.id, task.kind, task.input), ctx)
            meter.check()
        except BudgetExceeded as e:
            status, output, stop = BUDGET, {**ctx.partial, "_partial": True}, f"{e.limit}: {e.used}/{e.allowed}"
            ctx.log("stop", reason="budget", limit=e.limit)
        except ToolError as e:
            status, output, stop = ERROR, {**ctx.partial, "_partial": True}, f"unhandled tool error {e.tool}:{e.code}"
        except Exception as e:  # дефект системы — фиксируем, но прогон не роняем
            status, output, stop = ERROR, {**ctx.partial, "_partial": True}, f"{type(e).__name__}: {e}"
        results.append(Result(task.id, status, output, meter.usage(), stop, ctx.trace))
    return results


def _pct(xs: list[float], q: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))], 3)


def save_run(system: System, suite: str, budget: Budget, results: list[Result], metrics: dict,
             per_task: list[dict], started: datetime, wall: float, note: str = "", *, tasks: list[Task]) -> Path:
    run_id = f"{started.strftime('%Y%m%d-%H%M%S-%f')}_{system.name}_{suite}"
    out = RUNS / run_id
    out.mkdir(parents=True)
    secs = [r.usage["seconds"] for r in results]
    totals = {
        "tasks": len(results),
        "cost_usd": round(sum(r.usage["cost_usd"] for r in results), 4),
        "tokens_in": sum(r.usage["tokens_in"] for r in results),
        "tokens_out": sum(r.usage["tokens_out"] for r in results),
        "tool_calls": sum(r.usage["tool_calls"] for r in results),
        "wall_seconds": round(wall, 2),
        "task_seconds_p50": _pct(secs, 0.5), "task_seconds_p95": _pct(secs, 0.95),
    }
    meta = {
        "run_id": run_id, "started_at": started.isoformat(timespec="seconds"), "suite": suite, "note": note,
        "system": {"name": system.name, **system.config()},
        "budget_per_task": budget.__dict__, "eval_set": eval_fingerprint(), "git": git_state(),
        "python": platform.python_version(), "totals": totals,
    }
    meta["task_ids"] = [task.id for task in tasks]
    meta["task_overrides"] = {task.id: {k: task.input[k] for k in ("budget", "tool_limits", "faults")
                                       if k in task.input}
                              for task in tasks if task.kind == "scenario"}
    meta["tool_contracts"] = {name: spec.__dict__ for name, spec in CONTRACTS.items()}
    meta["harness_sha256"] = {p.relative_to(ROOT).as_posix(): sha256_file(p)
                              for p in sorted((ROOT / "harness").rglob("*")) if p.suffix in {".py", ".json"}}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(out / "results.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r.__dict__, ensure_ascii=False) + "\n")
    with open(out / "per_task.jsonl", "w", encoding="utf-8") as f:
        for row in per_task:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    index = RUNS / "index.csv"
    new = not index.exists()
    with open(index, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["run_id", "system", "model", "suite", "eval", "commit", "cost_usd", "wall_s", "metrics"])
        w.writerow([run_id, system.name, meta["system"].get("model", "-"), suite, EVAL_VERSION,
                    meta["git"]["commit"][:8], totals["cost_usd"], totals["wall_seconds"],
                    json.dumps({k: v for k, v in metrics.items() if not isinstance(v, (dict, list, tuple))})])
    return out


def now() -> tuple[datetime, float]:
    return datetime.now(timezone.utc), time.perf_counter()
