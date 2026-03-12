"""Tests for data-oriented logging levels (0, 1, 2).

Use only the public API: Session.from_config, make_env, session.inspect, RunConfig.
"""

import unittest

from doagent import Session, RunConfig, make_env
from experiments import run_gridworld_validation
from examples.gridworld_demo.env import create_gridworld_env
from examples.gridworld_demo.policies import (
    random_explore_policy,
    frontier_explore_policy,
)


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


def _session_config(logging_level: int) -> dict:
    return {
        "shared_data": {"type": "memory"},
        "run_config": {"logging_level": logging_level},
        "topology": {"mode": "centralised"},
        "policies": {
            "grid_random": random_explore_policy,
            "grid_frontier": frontier_explore_policy,
        },
    }


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

    def test_level_0_no_trace_no_explanation(self):
        """Level 0: agent_update and outcome; no trace; no decision.explanation."""
        config = _session_config(0)
        session = Session.from_config(config)
        env = self._make_env()

        run_gridworld_validation(
            session=session,
            env=env,
            configs=_agent_configs_with_explanation(),
            rounds=2,
            seed=123,
        )

        agent_updates = session.inspect("agent_update")
        traces = session.inspect("trace")
        outcomes = session.inspect("outcome")

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
        config = _session_config(1)
        session = Session.from_config(config)
        env = self._make_env()

        run_gridworld_validation(
            session=session,
            env=env,
            configs=_agent_configs_with_explanation(),
            rounds=2,
            seed=456,
        )

        agent_updates = session.inspect("agent_update")
        traces = session.inspect("trace")
        outcomes = session.inspect("outcome")

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
        config = _session_config(2)
        session = Session.from_config(config)
        env = self._make_env()

        run_gridworld_validation(
            session=session,
            env=env,
            configs=_agent_configs_with_explanation(),
            rounds=2,
            seed=789,
        )

        agent_updates = session.inspect("agent_update")
        traces = session.inspect("trace")
        outcomes = session.inspect("outcome")

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
        config = _session_config(2)  # default is 2
        session = Session.from_config(config)
        env = self._make_env()

        run_gridworld_validation(
            session=session,
            env=env,
            configs=_agent_configs_with_explanation(),
            rounds=1,
            seed=111,
        )

        traces = session.inspect("trace")
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
