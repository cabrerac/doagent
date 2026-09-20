"""Tests for the three-agent addition example."""

import json
import tempfile
import unittest
from pathlib import Path

from experiments._shared import output_bytes_from_path
from experiments.attribution.evaluate import evaluate_attribution
from experiments.attribution.projections import project_logging_level
from experiments.attribution.run import CHECKER, run_addition_team


class TestAdditionTeamExample(unittest.TestCase):
    def test_checker_is_labelled_when_it_accepts_a_wrong_sum(self):
        result = run_addition_team(
            {"a": 3, "b": 4},
            {"plant_wrong_sum": 8, "plant_accept_wrong": True},
            storage="memory",
        )
        gold = result["gold"]
        self.assertEqual(gold["gold_who"], CHECKER)
        self.assertEqual(gold["gold_when"], 2)
        self.assertEqual(result["assignment"], {"assignee": "solver", "op": "add", "a": 3, "b": 4})
        self.assertEqual(result["solver_value"], 8)

        session = result["session"]
        updates = session.inspect("agent_update")
        actors = [r.actor for r in updates]
        self.assertIn("orchestrator", actors)
        self.assertIn("solver", actors)
        self.assertIn("checker", actors)

        checker_view = session.decision_context("checker", kinds="agent_update")
        self.assertTrue(checker_view)
        self.assertTrue(all(r.actor == "orchestrator" for r in checker_view))

        check_updates = [
            r
            for r in updates
            if r.actor == "checker"
            and (r.payload.get("decision") or {})
            .get("response", {})
            .get("choice", {})
            .get("action", {})
            .get("type")
            == "check"
        ]
        self.assertEqual(len(check_updates), 1)
        action = check_updates[0].payload["decision"]["response"]["choice"]["action"]
        self.assertTrue(action["accept"])
        self.assertEqual(action["reported"], 8)
        self.assertEqual(action["correct"], 7)

        artifacts = result["artifacts"]
        self.assertEqual(set(artifacts), {"d0", "d1", "d2", "lookup"})
        self.assertEqual(artifacts["lookup"]["who"], CHECKER)
        self.assertEqual(artifacts["lookup"]["when"], 2)
        self.assertLess(len(artifacts["d0"]), len(artifacts["d2"]))
        self.assertTrue(all(step.get("kind") != "trace" for step in artifacts["d0"]))
        self.assertTrue(
            all(not (step.get("provenance") or {}) for step in artifacts["d0"])
        )
        self.assertFalse(
            any(
                (step.get("payload") or {}).get("decision", {}).get("explanation")
                for step in artifacts["d1"]
            )
        )

    def test_file_run_writes_reproducible_attribution_artifacts(self):
        with tempfile.TemporaryDirectory() as output_base:
            result = run_addition_team(
                {"a": 3, "b": 4},
                {"plant_wrong_sum": 8, "plant_accept_wrong": True},
                storage="file",
                output_base=output_base,
            )

            paths = result["artifact_paths"]
            self.assertEqual(
                set(paths),
                {"d0", "d1", "d2", "lookup", "manifest"},
            )
            for path in paths.values():
                self.assertTrue(Path(path).is_file())

            lookup = json.loads(Path(paths["lookup"]).read_text(encoding="utf-8"))
            self.assertEqual(lookup["who"], CHECKER)
            self.assertEqual(lookup["when"], 2)

            manifest = json.loads(Path(paths["manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["run_id"], result["session"].run_id)
            self.assertEqual(manifest["config"]["query"], {"a": 3, "b": 4})
            self.assertEqual(manifest["config"]["storage"], "file")
            self.assertTrue(manifest["config_hash"])

    def test_evaluate_measures_the_same_addition_run(self):
        result = evaluate_attribution(
            {"a": 3, "b": 4},
            {"plant_wrong_sum": 8, "plant_accept_wrong": True},
            storage="memory",
        )
        self.assertEqual(result.condition["storage"], "memory")
        self.assertEqual(result.condition["capture"], "d2")
        self.assertEqual(result.condition["logging_level"], 2)
        self.assertEqual(result.task_metrics["gold_who"], CHECKER)
        self.assertEqual(result.task_metrics["lookup_who"], CHECKER)
        self.assertEqual(result.task_metrics["lookup_when"], 2)
        self.assertGreaterEqual(result.elapsed_seconds, 0.0)
        self.assertEqual(result.output_bytes, 0)

    def test_projected_d0_matches_logging_rules(self) -> None:
        d2 = [
            {
                "kind": "agent_update",
                "provenance": {"created_by": "solver"},
                "accountability": {"owner": "solver"},
                "payload": {
                    "decision": {
                        "explanation": "drop me",
                        "response": {"reasoning": ["x"], "choice": {"action": {}}},
                    }
                },
            },
            {"kind": "trace", "payload": {"round": 1}, "provenance": {"a": 1}},
            {"kind": "outcome", "payload": {"round": 1}, "provenance": {"a": 1}},
        ]
        d0 = project_logging_level(d2, 0)
        d1 = project_logging_level(d2, 1)
        self.assertEqual([item["kind"] for item in d0], ["agent_update", "outcome"])
        self.assertEqual(d0[0]["provenance"], {})
        self.assertNotIn("explanation", d0[0]["payload"]["decision"])
        self.assertNotIn("reasoning", d0[0]["payload"]["decision"]["response"])
        self.assertEqual([item["kind"] for item in d1], ["agent_update", "trace", "outcome"])
        self.assertEqual(d1[0]["provenance"], {"created_by": "solver"})
        self.assertNotIn("explanation", d1[0]["payload"]["decision"])
        self.assertEqual(project_logging_level(d2, 2), d2)

    def test_live_d0_records_are_smaller_than_d2(self) -> None:
        with tempfile.TemporaryDirectory() as output_base:
            d0 = evaluate_attribution(
                {"a": 3, "b": 4},
                {"plant_wrong_sum": 8, "plant_accept_wrong": True},
                storage="file",
                output_base=output_base,
                logging_level=0,
            )
            d2 = evaluate_attribution(
                {"a": 3, "b": 4},
                {"plant_wrong_sum": 8, "plant_accept_wrong": True},
                storage="file",
                output_base=output_base,
                logging_level=2,
            )
            self.assertEqual(d0.condition["capture"], "d0")
            self.assertEqual(d2.condition["capture"], "d2")
            self.assertLess(d0.output_bytes, d2.output_bytes)
            self.assertGreater(d0.output_bytes, 0)
            self.assertEqual(
                d2.output_bytes,
                output_bytes_from_path(Path(d2.run_path) / "records"),
            )
            self.assertTrue((Path(d2.run_path) / "gold.json").is_file())


if __name__ == "__main__":
    unittest.main()
