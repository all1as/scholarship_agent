"""LLM-извлечение без сети: заглушка клиента отдаёт ответ «идеальной модели» по эталону.
Проверяется трубопровод (валидатор, повтор на невалидном JSON, учёт токенов/стоимости), а не качество модели.
Запуск: python -m unittest discover tests
"""

import json
import unittest
from types import SimpleNamespace

from harness.core import Budget
from harness.metrics import score_extract
from harness.runner import extract_tasks, run_tasks
from harness.systems.llm_extract import LLMExtract


class FakeClient:
    def __init__(self, labels, broken_first=False, hallucinate=False):
        self.labels, self.broken_first, self.hallucinate, self.calls = labels, broken_first, hallucinate, 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, model, messages, **kw):
        self.calls += 1
        url_line = messages[1]["content"].split("\n")[0]
        label = next(l for l in self.labels.values() if any(
            url_line.endswith(u) for u in self._urls(l)))
        page = self._page_for(label, url_line)
        dates = [dict(type="application", **{k: d[k] for k in ("date", "granularity", "cycle", "scope", "scope_detail", "quote")})
                 for d in label["application_deadlines"] if d["page"] == page]
        dates += [{k: d[k] for k in ("date", "granularity", "cycle", "type", "quote")} | {"scope": "global", "scope_detail": None}
                  for d in label["other_dates"] if d["page"] == page]
        if self.hallucinate:
            dates.append({"date": "2027-03-01", "granularity": "day", "type": "application", "cycle": "2027/28",
                          "scope": "global", "scope_detail": None, "quote": "Applications close on 1 March 2027"})
        a = label["amount"]
        amount = ({k: a[k] for k in ("value", "currency", "period", "full_coverage", "quote")}
                  if a and a["page"] == page else None)
        content = json.dumps({"dates": dates, "amount": amount})
        if self.broken_first and self.calls == 1:
            content = content[:20]
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
                               usage=SimpleNamespace(prompt_tokens=2600, completion_tokens=600))

    _manifest = None

    def _urls(self, label):
        from harness.tools import _manifest
        if FakeClient._manifest is None:
            FakeClient._manifest = _manifest()
        return [r["url"] for p, r in FakeClient._manifest.items() if p.startswith(label["id"] + "/")]

    def _page_for(self, label, url_line):
        return next(p for p, r in FakeClient._manifest.items()
                    if p.startswith(label["id"] + "/") and url_line.endswith(r["url"]) and "_" not in p.split("/")[1])


class LLMExtractPipeline(unittest.TestCase):
    ids = ["chevening", "eiffel", "lund_global", "commonwealth_masters", "nl_scholarship"]

    def run_with(self, **kw):
        tasks, labels = extract_tasks(self.ids)
        system = LLMExtract(client=FakeClient(labels, **kw), price=(0.25, 2.0))
        results = run_tasks(system, tasks, Budget())
        return results, score_extract(results, labels)[1]

    def test_perfect_model_scores_perfect(self):
        results, m = self.run_with()
        self.assertEqual(m["M4"], 1.0)
        self.assertEqual(m["M4_dangerous"], 0)
        self.assertEqual(m["M8a"], 0.0)
        self.assertGreater(sum(r.usage["cost_usd"] for r in results), 0)

    def test_invalid_json_retried_once(self):
        results, m = self.run_with(broken_first=True)
        first = results[0]
        self.assertTrue(any(e.get("code") == "invalid_json" for e in first.trace))
        self.assertEqual(m["M4"], 1.0)

    def test_hallucinated_quote_rejected(self):
        results, m = self.run_with(hallucinate=True)
        self.assertEqual(m["M8a"], 0.0)                     # выдуманная цитата не дошла до фактов
        self.assertTrue(all(any(x["reason"] == "цитата не найдена в снимке" for x in r.output["rejected"])
                            for r in results))


if __name__ == "__main__":
    unittest.main()
