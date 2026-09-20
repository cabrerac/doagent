"""Layering tests for repository examples and experiments."""

from dataclasses import fields
from pathlib import Path
import importlib.util
import unittest
from unittest.mock import Mock, patch

from examples._shared.environment import ParallelEnvWrapper, StepResult
from examples._shared.llm_client import LLMResponse


REMOVED_MODULES = (
    "examples.minimal_usage",
    "examples.llm_policy",
    "examples.gridworld_demo",
    "examples.push_demo",
    "examples.attribution_eval",
    "experiments.baseline",
    "experiments.environment",
    "experiments.run_gridworld_comparison",
    "experiments.run_push_comparison",
    "experiments.run_topology_comparison",
    "experiments.gridworld.scenario",
    "experiments.push.scenario",
    "experiments.multiprocess_interface",
    "experiments.gridworld.agents",
    "experiments.push.agents",
)


class TestRepositoryLayout(unittest.TestCase):
    def test_removed_compatibility_paths_are_gone(self):
        missing = [
            name
            for name in REMOVED_MODULES
            if importlib.util.find_spec(name) is not None
        ]
        self.assertEqual(missing, [])

    def test_canonical_example_entry_points_import(self):
        from examples.minimal.run import main as minimal_main
        from examples.push.run import main as push_main

        self.assertIsNotNone(importlib.util.find_spec("examples.gridworld.run"))
        self.assertTrue(callable(minimal_main))
        self.assertTrue(callable(push_main))

    def test_examples_do_not_import_experiments(self):
        examples_dir = Path(__file__).resolve().parents[1] / "examples"
        offenders = []
        for path in examples_dir.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "from experiments" in text or "import experiments" in text:
                offenders.append(str(path.relative_to(examples_dir)))
        self.assertEqual(offenders, [])

    def test_shared_environment_types_are_available(self):
        self.assertTrue(callable(ParallelEnvWrapper))
        self.assertIn("observations", {item.name for item in fields(StepResult)})

    def test_llm_response_is_serializable(self):
        response = LLMResponse(
            text="ok",
            provider="fake",
            requested_model="requested",
            response_model="returned",
            usage={
                "input_tokens": 3,
                "output_tokens": 2,
                "total_tokens": 5,
            },
        )
        self.assertEqual(response.to_dict()["usage"]["total_tokens"], 5)

    def test_evaluator_times_the_same_single_run_it_reports(self):
        from experiments.push.evaluate import evaluate_push

        session = Mock(run_id=None, run_path=None)
        reporter = Mock()
        reporter.metrics.return_value = {"outcomes": 4}
        with (
            patch(
                "experiments.push.evaluate.Session.from_config",
                return_value=session,
            ),
            patch("experiments.push.evaluate.RunReporter", return_value=reporter),
            patch("experiments.push.evaluate.make_env", return_value=object()),
            patch(
                "experiments.push.evaluate.make_agent_configs",
                return_value=[],
            ),
            patch(
                "experiments.push.evaluate.run_with_session",
                return_value=4,
            ) as run,
        ):
            result = evaluate_push(storage="memory", rounds=4, seed=7)

        run.assert_called_once()
        self.assertEqual(result.task_metrics["outcomes"], 4)
        self.assertGreaterEqual(result.elapsed_seconds, 0.0)


if __name__ == "__main__":
    unittest.main()
