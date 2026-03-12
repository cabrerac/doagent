"""Tests for data-oriented logging levels (0, 1, 2)."""

import unittest

from doagent import make_env
from doagent.core import InMemorySharedData, RunConfig
from experiments import (
    PolicyRegistry,
    run_gridworld_validation,
)
from examples.gridworld_demo.env import create_gridworld_env
from examples.gridworld_demo.policies import register_gridworld_policies


def _agent_configs_with_explanation():
    """Agent configs that include explanation in metadata."""
    return [
        {
            "id": "agent_0",
            "policy": {"name": "grid_random", "params": {"seed": 1}},
            "metadata": {"explanation": "Random exploration policy."},
        },
        {
            "id": "agent_1",
            "policy": {"name": "grid_frontier", "params": {"seed": 2}},
            "metadata": {"explanation": "Frontier-based exploration."},
        },
    ]


class TestLoggingLevels(unittest.TestCase):
    def _make_env(self):
        return make_env(
            create_gridworld_env,
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

    def test_level_0_no_trace_no_explanation(self):
        """Level 0: agent_update and outcome; no trace; no decision.explanation."""
        shared_data = InMemorySharedData()
        env = self._make_env()
        registry = self._make_registry()
        run_config = RunConfig.with_logging_level(0)

        run_gridworld_validation(
            shared_data=shared_data,
            env=env,
            registry=registry,
            configs=_agent_configs_with_explanation(),
            rounds=2,
            seed=123,
            run_config=run_config,
        )

        agent_updates = list(shared_data.listen("agent_update"))
        traces = list(shared_data.listen("trace"))
        outcomes = list(shared_data.listen("outcome"))

        self.assertEqual(len(agent_updates), 4, "4 agent_updates (2 agents x 2 rounds)")
        self.assertEqual(len(outcomes), 2, "2 outcomes")
        self.assertEqual(len(traces), 0, "No traces at level 0")

        for record in agent_updates:
            self.assertIn("decision", record.payload)
            self.assertNotIn("explanation", record.payload["decision"])
            self.assertIn("local_knowledge", record.payload)
        for record in outcomes:
            self.assertEqual(record.provenance, {})
            self.assertEqual(record.accountability, {})

    def test_level_1_trace_and_explanation(self):
        """Level 1: adds trace and decision.explanation."""
        shared_data = InMemorySharedData()
        env = self._make_env()
        registry = self._make_registry()
        run_config = RunConfig.with_logging_level(1)

        run_gridworld_validation(
            shared_data=shared_data,
            env=env,
            registry=registry,
            configs=_agent_configs_with_explanation(),
            rounds=2,
            seed=456,
            run_config=run_config,
        )

        agent_updates = list(shared_data.listen("agent_update"))
        traces = list(shared_data.listen("trace"))
        outcomes = list(shared_data.listen("outcome"))

        self.assertEqual(len(agent_updates), 4)
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(len(traces), 4, "4 traces (2 agents x 2 rounds)")

        for record in agent_updates:
            self.assertIn("decision", record.payload)
            self.assertIn("explanation", record.payload["decision"])
        for record in outcomes:
            self.assertEqual(record.provenance, {})
            self.assertEqual(record.accountability, {})

    def test_level_2_provenance_and_accountability(self):
        """Level 2: adds provenance and accountability on envelope."""
        shared_data = InMemorySharedData()
        env = self._make_env()
        registry = self._make_registry()
        run_config = RunConfig.with_logging_level(2)

        run_gridworld_validation(
            shared_data=shared_data,
            env=env,
            registry=registry,
            configs=_agent_configs_with_explanation(),
            rounds=2,
            seed=789,
            run_config=run_config,
        )

        agent_updates = list(shared_data.listen("agent_update"))
        traces = list(shared_data.listen("trace"))
        outcomes = list(shared_data.listen("outcome"))

        self.assertEqual(len(agent_updates), 4)
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(len(traces), 4)

        for record in agent_updates + outcomes:
            self.assertGreater(
                len(record.provenance),
                0,
                f"Record {record.id} should have provenance",
            )
            self.assertGreater(
                len(record.accountability),
                0,
                f"Record {record.id} should have accountability",
            )

    def test_default_level_2(self):
        """Default run_config yields level 2 behaviour."""
        shared_data = InMemorySharedData()
        env = self._make_env()
        registry = self._make_registry()

        run_gridworld_validation(
            shared_data=shared_data,
            env=env,
            registry=registry,
            configs=_agent_configs_with_explanation(),
            rounds=1,
            seed=111,
        )

        traces = list(shared_data.listen("trace"))
        self.assertGreater(len(traces), 0, "Default should write traces")

    def test_run_config_validation_rejects_invalid_level(self):
        """RunConfig rejects invalid logging levels."""
        with self.assertRaises(ValueError):
            RunConfig(logging_level=3)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            RunConfig.with_logging_level(-1)
        with self.assertRaises(ValueError):
            RunConfig.with_logging_level(99)


if __name__ == "__main__":
    unittest.main(verbosity=2)
