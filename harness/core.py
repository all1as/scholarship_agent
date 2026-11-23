"""Общие типы харнесса: задача, результат, бюджет, интерфейс системы.

Любая система (baseline B1, LLM-извлечение, агент) реализует один интерфейс System.run(task, ctx),
поэтому запускается одним и тем же раннером на одном и том же наборе.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol


# ---------- бюджет и критерий остановки ----------

@dataclass(frozen=True)
class Budget:
    """Лимиты на одну задачу. При исчерпании любого — BudgetExceeded, раннер сохраняет частичный результат."""
    max_steps: int = 8              # шаг = один вызов модели или один ход агента
    max_tool_calls: int = 20        # все инструменты вместе; у каждого инструмента ещё свой лимит
    max_cost_usd: float = 0.05
    max_seconds: float = 120.0


class BudgetExceeded(Exception):
    def __init__(self, limit: str, used: Any, allowed: Any):
        super().__init__(f"budget exhausted: {limit} used={used} allowed={allowed}")
        self.limit, self.used, self.allowed = limit, used, allowed


@dataclass
class Meter:
    """Счётчик ресурсов одной задачи: шаги, токены, стоимость, вызовы инструментов, время."""
    budget: Budget
    steps: int = 0
    tool_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    t0: float = field(default_factory=time.perf_counter)

    def elapsed(self) -> float:
        return time.perf_counter() - self.t0

    def check(self) -> None:
        b = self.budget
        if self.steps > b.max_steps:
            raise BudgetExceeded("steps", self.steps, b.max_steps)
        if self.tool_calls > b.max_tool_calls:
            raise BudgetExceeded("tool_calls", self.tool_calls, b.max_tool_calls)
        if self.cost_usd > b.max_cost_usd:
            raise BudgetExceeded("cost_usd", round(self.cost_usd, 4), b.max_cost_usd)
        if self.elapsed() > b.max_seconds:
            raise BudgetExceeded("seconds", round(self.elapsed(), 1), b.max_seconds)

    def step(self) -> None:
        """Учитывает только шаги, допущенные бюджетом."""
        self.check()
        if self.steps >= self.budget.max_steps:
            raise BudgetExceeded("steps", self.steps, self.budget.max_steps)
        self.steps += 1

    def tool_call(self) -> None:
        self.check()
        if self.tool_calls >= self.budget.max_tool_calls:
            raise BudgetExceeded("tool_calls", self.tool_calls, self.budget.max_tool_calls)
        self.tool_calls += 1

    def charge(self, tokens_in: int, tokens_out: int, cost_usd: float) -> None:
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        self.cost_usd += cost_usd

    def usage(self) -> dict:
        return {"steps": self.steps, "tool_calls": self.tool_calls, "tokens_in": self.tokens_in,
                "tokens_out": self.tokens_out, "cost_usd": round(self.cost_usd, 6),
                "seconds": round(self.elapsed(), 3)}


# ---------- задача, контекст, результат ----------

@dataclass
class Task:
    id: str
    kind: str                       # "extract" | "scenario"
    input: dict
    expected: dict | None = None    # эталон; системе не передаётся


@dataclass
class Context:
    """То, что система получает на задачу: инструменты, счётчик и место для частичного результата."""
    tools: Any                      # harness.tools.Toolbox
    meter: Meter
    trace: list[dict] = field(default_factory=list)
    partial: dict = field(default_factory=dict)   # система пишет сюда по ходу работы — это и есть частичный результат

    def log(self, event: str, **data: Any) -> None:
        self.trace.append({"t": round(self.meter.elapsed(), 3), "event": event, **data})


# Статусы завершения задачи. "крутится дальше" невозможно: раннер всегда получает один из них.
OK = "ok"                       # система закончила сама
PARTIAL = "partial"             # закончила, но часть данных не получена (ошибка инструмента, деградация)
BUDGET = "budget_exhausted"     # остановлена по бюджету, output = частичный результат
REFUSED = "refused"             # отказ по контракту (вне домена и т.п.)
ERROR = "error"                 # необработанная ошибка системы — дефект, считается в метриках как неверный ответ


@dataclass
class Result:
    task_id: str
    status: str
    output: dict
    usage: dict
    stop_reason: str | None = None
    trace: list[dict] = field(default_factory=list)


class System(Protocol):
    name: str

    def config(self) -> dict:
        """Всё, что влияет на результат: модель с версией, температура, seed, тексты/хэши промптов, версия правил."""

    def run(self, task: Task, ctx: Context) -> tuple[str, dict]:
        """Возвращает (статус OK/PARTIAL/REFUSED, output). Бюджет и ошибки инструментов обрабатывает сама или пробрасывает."""
