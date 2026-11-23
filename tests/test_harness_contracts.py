import unittest

from unittest.mock import patch

from harness.context import build_context
from harness.core import BUDGET, ERROR, PARTIAL, Budget, OK, Result, Task
from harness.metrics import score_extract
from harness.runner import extract_tasks, run_tasks
from harness.systems.llm_extract import quote_in_snapshot
from harness.tools import ToolError, _manifest


class HarnessContracts(unittest.TestCase):
    def test_incomplete_runs_do_not_get_credit_for_unverified_absence(self):
        tasks, labels = extract_tasks()
        for status in (ERROR, PARTIAL, BUDGET):
            with self.subTest(status=status):
                results = [Result(task.id, status, {}, {}) for task in tasks]
                _, metrics = score_extract(results, labels)
                self.assertEqual((metrics["M4"], metrics["M5"]), (0.0, 0.0))

    def test_empty_quote_is_not_evidence(self):
        for quote in ("", " \t\n", None):
            with self.subTest(quote=quote):
                self.assertFalse(quote_in_snapshot({"quote": quote}, "source text"))
        self.assertTrue(quote_in_snapshot({"quote": "source text"}, "source text"))

    def test_unreadable_snapshot_is_typed_in_both_tools(self):
        class Probe:
            def run(self, task, ctx):
                codes = {}
                for tool in (ctx.tools.fetch, ctx.tools.fetch_alt):
                    try:
                        tool("chevening/1.txt")
                    except ToolError as exc:
                        codes[exc.tool] = exc.code
                return OK, codes

        with patch("harness.tools.Path.read_text", side_effect=PermissionError):
            result, = run_tasks(Probe(), [Task("probe", "extract", {})], Budget())
        self.assertEqual(result.output, {"fetch": "snapshot_error", "fetch_alt": "snapshot_error"})

    def test_fallback_cannot_read_heldout_snapshot(self):
        from harness.runner import visible_ids

        visible = visible_ids()
        page = next(p for p in _manifest() if p.split("/")[0] not in visible)

        class Probe:
            def run(self, task, ctx):
                with self_test.assertRaises(ToolError) as raised:
                    ctx.tools.fetch_alt(page)
                return OK, {"code": raised.exception.code}

        self_test = self
        result, = run_tasks(Probe(), [Task("probe", "extract", {})], Budget())
        self.assertEqual((result.status, result.output), (OK, {"code": "not_found"}))

    def test_budget_disallows_extra_step_and_preserves_partial_output(self):
        class Probe:
            def run(self, task, ctx):
                ctx.meter.step()
                ctx.partial["done"] = 1
                ctx.meter.step()
                raise AssertionError("extra step ran")

        result, = run_tasks(Probe(), [Task("probe", "extract", {})], Budget(max_steps=1))
        self.assertEqual(result.status, BUDGET)
        self.assertEqual(result.usage["steps"], 1)
        self.assertEqual(result.output, {"done": 1, "_partial": True})

    def test_context_trimming_does_not_mutate_l3(self):
        l3 = {"today": "2026-10-25", "nearest": ["x" * 400], "attention": []}
        context = build_context("system", {}, l3, [], [], "y" * 400,
                                budget={"l3": 25, "history": 10})
        self.assertEqual(l3["nearest"], ["x" * 400])
        self.assertLessEqual(context["tokens"]["l3"], 25)
        self.assertLessEqual(context["tokens"]["history"], 10)
