import unittest

from harness.context import build_context
from harness.core import BUDGET, Budget, OK, Task
from harness.runner import run_tasks
from harness.tools import ToolError, _manifest


class HarnessContracts(unittest.TestCase):
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
