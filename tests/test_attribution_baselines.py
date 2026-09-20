"""Tests for independent W/T collectors and the no-DOAgent host loop."""

import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.attribution.baselines import (
    OutputLogCollector,
    StepIOCollector,
    run_direct_team,
)
from experiments.attribution.evaluate import evaluate_baseline_cost
from experiments.attribution.labels import CHECKER
from experiments.attribution.run import run_addition_team


QUERY = {"a": 3, "b": 4}
PLANT = {"plant_wrong_sum": 8, "plant_accept_wrong": True}


class TestAttributionBaselines(unittest.TestCase):
    def test_direct_team_does_not_import_doagent(self) -> None:
        host = (
            Path(__file__).resolve().parents[1]
            / "experiments"
            / "attribution"
            / "baselines"
            / "host.py"
        )
        tree = ast.parse(host.read_text(encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        self.assertTrue(all(not name.startswith("doagent") for name in imported))

    def test_direct_team_matches_doagent_gold_and_actions(self) -> None:
        direct = run_direct_team(QUERY, PLANT)
        hosted = run_addition_team(QUERY, PLANT, storage="memory")
        self.assertEqual(direct["gold"]["gold_who"], CHECKER)
        self.assertEqual(direct["gold"]["gold_when"], 2)
        self.assertEqual(direct["assignment"], hosted["assignment"])
        self.assertEqual(direct["solver_value"], hosted["solver_value"])

    def test_w_omits_inputs_and_t_keeps_them(self) -> None:
        w_log = OutputLogCollector()
        t_log = StepIOCollector()
        run_direct_team(QUERY, PLANT, collectors=(w_log, t_log))
        w_steps = w_log.steps()
        t_steps = t_log.steps()
        self.assertEqual([step["step"] for step in w_steps], [0, 1, 2])
        self.assertTrue(all("input" not in step for step in w_steps))
        self.assertTrue(all("content" in step for step in w_steps))
        self.assertTrue(all("input" in step for step in t_steps))
        self.assertEqual(
            [step["content"] for step in w_steps],
            [step["output"] for step in t_steps],
        )
        self.assertEqual(w_steps[1]["content"]["type"], "solve")
        self.assertEqual(t_steps[1]["input"]["assignment"]["a"], 3)
        dumped = json.dumps(w_steps + t_steps)
        self.assertNotIn("explanation", dumped)
        self.assertNotIn("observation", dumped)

    def test_observe_only_collectors_do_not_change_gold(self) -> None:
        w_log = OutputLogCollector()
        t_log = StepIOCollector()
        result = run_addition_team(
            QUERY,
            PLANT,
            storage="memory",
            collectors=(w_log, t_log),
        )
        self.assertEqual(result["gold"]["gold_who"], CHECKER)
        self.assertEqual(result["gold"]["gold_when"], 2)
        self.assertEqual(result["packs"]["w"][2]["agent"], CHECKER)
        self.assertEqual(result["packs"]["w"][2]["content"]["type"], "check")
        self.assertNotIn("input", result["packs"]["w"][0])
        self.assertIn("solver_value", result["packs"]["t"][2]["input"])
        self.assertNotIn("observation", result["packs"]["t"][0]["input"])

    def test_baseline_cost_times_the_direct_loop(self) -> None:
        with tempfile.TemporaryDirectory() as output_base:
            measured = evaluate_baseline_cost(
                QUERY,
                PLANT,
                capture="w",
                output_base=output_base,
            )
            self.assertEqual(measured.condition["capture"], "w")
            self.assertEqual(measured.condition["storage"], "direct")
            self.assertGreaterEqual(measured.elapsed_seconds, 0.0)
            self.assertGreater(measured.output_bytes, 0)
            self.assertEqual(measured.task_metrics["gold_who"], CHECKER)
            pack = Path(measured.run_path) / "who_when.json"
            self.assertTrue(pack.is_file())
            self.assertEqual(measured.output_bytes, pack.stat().st_size)

    def test_accuracy_runner_writes_collector_packs_then_judges(self) -> None:
        from experiments.runners.attribution_comparison import (
            run_attribution_accuracy,
        )

        with tempfile.TemporaryDirectory() as output_base:
            with patch(
                "experiments.runners.attribution_comparison.run_judges"
            ) as judges:
                judges.return_value = {}
                scores_path = run_attribution_accuracy(QUERY, PLANT, output_base)
            run_dir = Path(judges.call_args[0][0])
            analysis = run_dir / "analysis" / "attribution"
            who_when = json.loads(
                (analysis / "who_when.json").read_text(encoding="utf-8")
            )
            trace = json.loads(
                (analysis / "trace_elephant.json").read_text(encoding="utf-8")
            )
            d0 = json.loads((analysis / "d0.json").read_text(encoding="utf-8"))
            d2 = json.loads((analysis / "d2.json").read_text(encoding="utf-8"))
            self.assertEqual(who_when[2]["content"]["type"], "check")
            self.assertIn("solver_value", trace[2]["input"])
            self.assertLess(len(d0), len(d2))
            self.assertTrue(all(item.get("kind") != "trace" for item in d0))
            self.assertEqual(scores_path, analysis / "scores.json")
            judges.assert_called_once()


if __name__ == "__main__":
    unittest.main()
