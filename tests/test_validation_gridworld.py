"""Tests for grid-world validation scenario.

Use only the public API: Session.from_config, make_env, session.inspect.
"""

import tempfile
import unittest
from pathlib import Path

from doagent import Session, make_env
from experiments import (
    run_gridworld_validation,
    output_bytes_from_path,
)
from examples.gridworld_demo.env import create_gridworld_env
from examples.gridworld_demo.policies import (
    random_explore_policy,
    frontier_explore_policy,
)


def _agent_configs():
    return [
        {"id": "agent_0", "policy": {"name": "grid_random", "params": {"seed": 1}}},
        {"id": "agent_1", "policy": {"name": "grid_frontier", "params": {"seed": 2}}},
    ]


def _session_config(shared_data_type: str = "memory", path: str | None = None) -> dict:
    cfg = {
        "shared_data": {"type": shared_data_type},
        "run_config": {"logging_level": 2},
        "topology": {"mode": "centralised"},
        "policies": {
            "grid_random": random_explore_policy,
            "grid_frontier": frontier_explore_policy,
        },
    }
    if path is not None:
        cfg["shared_data"]["path"] = path
    return cfg


class TestGridWorldValidation(unittest.TestCase):
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

    def test_validation_with_in_memory_adapter(self):
        config = _session_config("memory")
        session = Session.from_config(config)
        env = self._make_env()

        summary = run_gridworld_validation(
            session=session,
            env=env,
            configs=_agent_configs(),
            rounds=3,
            seed=123,
        )

        agent_updates = session.inspect("agent_update")
        traces = session.inspect("trace")
        outcomes = session.inspect("outcome")

        self.assertEqual(summary.rounds, 3)
        self.assertEqual(summary.outcomes, 3)
        self.assertEqual(summary.total_cells, 16)
        self.assertGreaterEqual(summary.coverage, 0.0)
        self.assertLessEqual(summary.coverage, 1.0)
        self.assertEqual(len(agent_updates), 6)
        self.assertEqual(len(traces), 6)
        self.assertEqual(len(outcomes), 3)
        for record in agent_updates:
            self.assertIn("decision", record.payload)
            self.assertIn("local_knowledge", record.payload)
        self.assertEqual(set(summary.contributions.keys()), {"agent_0", "agent_1"})
        self.assertLessEqual(sum(summary.contributions.values()), summary.total_cells)
        if summary.discovery_round is not None:
            self.assertGreaterEqual(summary.discovery_round, 0)
            self.assertLessEqual(summary.discovery_round, summary.rounds)

    def test_validation_with_file_adapter(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _session_config("file", path=temp_dir)
            session = Session.from_config(config)
            env = self._make_env()

            summary = run_gridworld_validation(
                session=session,
                env=env,
                configs=_agent_configs(),
                rounds=2,
                seed=321,
            )

            agent_updates = session.inspect("agent_update")
            outcomes = session.inspect("outcome")

            self.assertEqual(summary.outcomes, 2)
            self.assertEqual(len(agent_updates), 4)
            self.assertEqual(len(outcomes), 2)
            self.assertGreater(output_bytes_from_path(temp_dir), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
