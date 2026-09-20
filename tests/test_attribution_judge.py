"""Offline tests for attribution judges."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from examples._shared.llm_client import LLMResponse
from experiments.attribution.judge import judge_view, run_judges
from experiments.attribution.score import score_attribution_results


class FakeClient:
    """Return fixed JSON responses and retain prompts for assertions."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.messages = []

    def __call__(self, *, model, messages, temperature):
        self.messages.append(messages)
        text = self.responses.pop(0)
        return LLMResponse(
            text=text,
            provider="fake",
            requested_model=model,
            response_model=f"{model}-snapshot",
            usage={
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
            },
        )


EVIDENCE = [
    {"step": 0, "agent": "orchestrator", "output": {"action": "assign"}},
    {"step": 1, "agent": "solver", "output": {"value": 8}},
    {
        "step": 2,
        "agent": "checker",
        "output": {"accept": True, "reported": 8, "correct": 7},
    },
]


def _d_record(step: int, agent: str, output: dict) -> dict:
    """Native-looking D record grouped by decision round."""
    return {
        "id": f"r{step}",
        "actor": agent,
        "kind": "agent_update",
        "payload": {
            "decision": {
                "request": {"context": {"round": step}, "inputs": {}},
                "response": output,
            }
        },
    }


D_EVIDENCE = [
    _d_record(0, "orchestrator", {"action": "assign"}),
    _d_record(1, "solver", {"value": 8}),
    _d_record(2, "checker", {"accept": True, "reported": 8, "correct": 7}),
]


class TestAttributionJudge(unittest.TestCase):
    def test_all_at_once_returns_prediction_and_usage(self):
        client = FakeClient(
            ['{"who":"checker","when":2,"reason":"accepted wrong value"}']
        )
        result = judge_view(
            method="all_at_once",
            view="w",
            task={"a": 3, "b": 4, "correct": 7},
            evidence=EVIDENCE,
            client=client,
        )
        self.assertEqual(result["prediction"]["who"], "checker")
        self.assertEqual(result["prediction"]["when"], 2)
        self.assertEqual(result["usage"]["total_tokens"], 15)

    def test_step_by_step_stops_at_first_reported_failure(self):
        client = FakeClient(
            [
                '{"failure_found":false,"who":null,"when":null,"reason":"ok"}',
                '{"failure_found":false,"who":null,"when":null,"reason":"ok"}',
                '{"failure_found":true,"who":"checker","when":2,"reason":"missed check"}',
            ]
        )
        result = judge_view(
            method="step_by_step",
            view="t",
            task={"a": 3, "b": 4},
            evidence=EVIDENCE,
            client=client,
        )
        self.assertEqual(result["prediction"]["who"], "checker")
        self.assertEqual(len(result["calls"]), 3)
        self.assertEqual(result["usage"]["total_tokens"], 45)

    def test_binary_search_narrows_then_attributes(self):
        client = FakeClient(
            [
                '{"half":"upper","reason":"later failure"}',
                '{"who":"checker","when":2,"reason":"missed check"}',
            ]
        )
        result = judge_view(
            method="binary_search",
            view="w",
            task={"a": 3, "b": 4},
            evidence=EVIDENCE,
            client=client,
        )
        self.assertEqual(result["prediction"]["when"], 2)
        self.assertEqual(len(result["calls"]), 2)

    def test_attribution_labels_are_not_added_to_prompts(self):
        client = FakeClient(
            ['{"who":"checker","when":2,"reason":"accepted wrong value"}']
        )
        judge_view(
            method="all_at_once",
            view="w",
            task={"a": 3, "b": 4},
            evidence=EVIDENCE,
            client=client,
        )
        prompt = json.dumps(client.messages)
        self.assertNotIn("gold_who", prompt)
        self.assertNotIn("gold_when", prompt)
        self.assertNotIn("plant_wrong_sum", prompt)

    def test_scores_compare_judges_and_lookup_to_gold(self):
        scores = score_attribution_results(
            gold={"gold_who": "checker", "gold_when": 2},
            lookup={"who": "checker", "when": 2},
            judges={
                "all_at_once": {
                    "w": {
                        "prediction": {"who": "solver", "when": 1},
                        "usage": {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
                    }
                }
            },
        )
        self.assertTrue(scores["lookup"]["who_match"])
        self.assertTrue(scores["lookup"]["when_match"])
        self.assertEqual(scores["lookup"]["usage"]["total_tokens"], 0)
        self.assertFalse(scores["judges"]["all_at_once"]["w"]["who_match"])
        self.assertEqual(scores["judges"]["all_at_once"]["w"]["usage"]["total_tokens"], 6)

    def test_run_judges_writes_scores_without_network(self):
        responses = (
            ['{"who":"checker","when":2,"reason":"accepted"}'] * 5
            + ['{"failure_found":true,"who":"checker","when":2,"reason":"accepted"}'] * 5
            + [
                '{"half":"upper","reason":"later"}',
                '{"who":"checker","when":2,"reason":"accepted"}',
            ]
            * 5
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            artifact_dir = run_dir / "analysis" / "attribution"
            artifact_dir.mkdir(parents=True)
            (run_dir / "gold.json").write_text(
                json.dumps(
                    {
                        "gold_who": "checker",
                        "gold_when": 2,
                        "query": {"a": 3, "b": 4, "correct": 7},
                    }
                ),
                encoding="utf-8",
            )
            (artifact_dir / "w.json").write_text(
                json.dumps([{"step": 0, "marker": "PROJECTED_ONLY"}]),
                encoding="utf-8",
            )
            (artifact_dir / "who_when.json").write_text(
                json.dumps(EVIDENCE),
                encoding="utf-8",
            )
            (artifact_dir / "trace_elephant.json").write_text(
                json.dumps(EVIDENCE),
                encoding="utf-8",
            )
            for name in ("d0", "d1", "d2"):
                (artifact_dir / f"{name}.json").write_text(
                    json.dumps(D_EVIDENCE),
                    encoding="utf-8",
                )
            (artifact_dir / "lookup.json").write_text(
                json.dumps({"who": "checker", "when": 2}),
                encoding="utf-8",
            )
            client = FakeClient(responses)
            with patch(
                "experiments.attribution.judge.create_llm_client",
                return_value=client,
            ):
                run_judges(run_dir)

            scores = json.loads(
                (artifact_dir / "scores.json").read_text(encoding="utf-8")
            )
            self.assertTrue(scores["lookup"]["who_match"])
            self.assertEqual(scores["lookup"]["usage"]["total_tokens"], 0)
            self.assertTrue(scores["judges"]["all_at_once"]["w"]["who_match"])
            self.assertGreater(
                scores["judges"]["all_at_once"]["w"]["usage"]["total_tokens"],
                0,
            )
            self.assertNotIn("PROJECTED_ONLY", json.dumps(client.messages))


if __name__ == "__main__":
    unittest.main()
