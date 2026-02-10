"""Tests for grid-world validation scenario."""

import tempfile
import unittest
from pathlib import Path

from doagent.core import FileSharedData, InMemorySharedData
from doagent.validation import (
    PolicyRegistry,
    make_grid_env,
    register_gridworld_policies,
    run_gridworld_validation,
    output_bytes_from_path,
)


def _agent_configs():
    return [
        {"id": "agent_0", "policy": {"name": "grid_random", "params": {"seed": 1}}},
        {"id": "agent_1", "policy": {"name": "grid_frontier", "params": {"seed": 2}}},
    ]


class TestGridWorldValidation(unittest.TestCase):
    def _make_env(self):
        return make_grid_env(
            width=4,
            height=4,
            agent_ids=["agent_0", "agent_1"],
            landmarks=2,
            observation_radius=1,
            max_cycles=10,
            seed=7,
        )

    def _make_registry(self):
        registry = PolicyRegistry()
        register_gridworld_policies(registry)
        return registry

    def test_validation_with_in_memory_adapter(self):
        shared_data = InMemorySharedData()
        env = self._make_env()
        registry = self._make_registry()

        summary = run_gridworld_validation(
            shared_data=shared_data,
            env=env,
            registry=registry,
            configs=_agent_configs(),
            rounds=3,
            seed=123,
        )

        decisions = list(shared_data.listen("decision"))
        explanations = list(shared_data.listen("explanation"))
        traces = list(shared_data.listen("trace"))
        outcomes = list(shared_data.listen("outcome"))
        updates = list(shared_data.listen("agent_update"))

        self.assertEqual(summary.rounds, 3)
        self.assertEqual(summary.outcomes, 3)
        self.assertEqual(summary.total_cells, 16)
        self.assertGreaterEqual(summary.coverage, 0.0)
        self.assertLessEqual(summary.coverage, 1.0)
        self.assertEqual(len(decisions), 6)
        self.assertEqual(len(explanations), 6)
        self.assertEqual(len(traces), 6)
        self.assertEqual(len(outcomes), 3)
        self.assertEqual(len(updates), 6)
        self.assertEqual(set(summary.contributions.keys()), {"agent_0", "agent_1"})
        self.assertLessEqual(sum(summary.contributions.values()), summary.total_cells)
        if summary.discovery_round is not None:
            self.assertGreaterEqual(summary.discovery_round, 0)
            self.assertLessEqual(summary.discovery_round, summary.rounds)

    def test_validation_with_file_adapter(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "records.jsonl"
            shared_data = FileSharedData(path)
            env = self._make_env()
            registry = self._make_registry()

            summary = run_gridworld_validation(
                shared_data=shared_data,
                env=env,
                registry=registry,
                configs=_agent_configs(),
                rounds=2,
                seed=321,
            )

            decisions = list(shared_data.listen("decision"))
            outcomes = list(shared_data.listen("outcome"))

            self.assertEqual(summary.outcomes, 2)
            self.assertEqual(len(decisions), 4)
            self.assertEqual(len(outcomes), 2)
            self.assertGreater(output_bytes_from_path(path), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
