"""Integration tests: Session + real env + real policies + real wiring.

These catch bugs that unit tests with stubs miss -- verifying that
observations, policies, shared maps, and actions are wired correctly
end-to-end.

Uses the config-driven Session API (Session.from_config) with no
doagent.core or doagent.records imports.
"""

import unittest
from typing import Any, Dict, List, Tuple

from doagent import Session, make_env
from examples.gridworld_demo.env import create_gridworld_env
from examples.gridworld_demo.policies import (
    random_explore_policy,
    frontier_explore_policy,
    auction_frontier_policy,
)

GRIDWORLD_POLICIES = {
    "grid_random": random_explore_policy,
    "grid_frontier": frontier_explore_policy,
    "grid_auction_frontier": auction_frontier_policy,
}


def _build_shared_map(records: List[Any]) -> Dict[str, Any]:
    """Same logic as the example -- must stay in sync."""
    cells: Dict[Tuple[int, int], str] = {}
    for record in records:
        local_knowledge = record.payload.get("local_knowledge", {})
        observation = local_knowledge.get("observation", {})
        cell_list = (
            observation.get("cells", [])
            or local_knowledge.get("cells", [])
            or record.payload.get("cells", [])
        )
        for cell in cell_list:
            x, y = cell.get("x"), cell.get("y")
            if x is not None and y is not None:
                cells[(x, y)] = cell.get("value", "unknown")
    return {"cells": [{"x": x, "y": y, "value": v} for (x, y), v in cells.items()]}


class TestSessionIntegration(unittest.TestCase):
    """Full-stack integration: config-driven Session + GridWorldEnv + real policies."""

    def _make_session_and_agents(self, agent_ids, *, topology_mode="centralised", visibility=None):
        configs = [
            {"id": aid, "policy": {"name": "grid_frontier", "params": {"seed": i}}, "metadata": {}}
            for i, aid in enumerate(agent_ids)
        ]
        session_cfg: Dict[str, Any] = {
            "shared_data": {"type": "memory"},
            "run_config": {"logging_level": 2},
            "topology": {"mode": topology_mode},
            "policies": GRIDWORLD_POLICIES,
        }
        if visibility:
            session_cfg["topology"]["visibility"] = visibility

        session = Session.from_config(session_cfg)
        env = make_env(create_gridworld_env, width=6, height=6, agent_ids=agent_ids, max_cycles=50, seed=42)
        wrapped_env = session.wrap_env(env, env_actor="gridworld_env")
        agents = session.create_agents(configs, goal="map_discovery", payload_type="map_update")
        return session, wrapped_env, agents

    def test_policies_receive_correct_observation_structure(self):
        """Policies must get position, width, height, cells in inputs.observation."""
        session, env, agents = self._make_session_and_agents(["a"])
        observations = env.reset(seed=42)
        obs = observations["a"]

        self.assertIn("position", obs)
        self.assertIn("x", obs["position"])
        self.assertIn("y", obs["position"])
        self.assertIn("width", obs)
        self.assertIn("height", obs)
        self.assertIn("cells", obs)
        self.assertGreater(len(obs["cells"]), 0)

    def test_agents_actually_move(self):
        """After several rounds, agent positions must change (not stuck)."""
        session, env, agents = self._make_session_and_agents(["a", "b"])
        observations = env.reset(seed=42)
        initial_positions = {
            aid: (obs["position"]["x"], obs["position"]["y"])
            for aid, obs in observations.items()
        }

        for round_id in range(1, 11):
            actions = {}
            for aid, agent in agents.items():
                shared_records = session.visible_records(aid, kind="agent_update")
                shared_map = _build_shared_map(shared_records)
                result = agent.decide(observations[aid], round_id, inputs={
                    "observation": observations[aid],
                    "shared_map": shared_map,
                })
                actions[aid] = result["action"]
            step = env.step(actions)
            observations = step["observations"]

        final_positions = {
            aid: (obs["position"]["x"], obs["position"]["y"])
            for aid, obs in observations.items()
        }

        moved = sum(1 for aid in initial_positions if initial_positions[aid] != final_positions[aid])
        self.assertGreater(moved, 0, "At least one agent should have moved after 10 rounds")

    def test_shared_map_accumulates_cells(self):
        """After a few rounds, visible_records should yield cells that grow the shared map."""
        session, env, agents = self._make_session_and_agents(["a"])
        observations = env.reset(seed=42)

        for round_id in range(1, 6):
            shared_records = session.visible_records("a", kind="agent_update")
            shared_map = _build_shared_map(shared_records)
            result = agents["a"].decide(observations["a"], round_id, inputs={
                "observation": observations["a"],
                "shared_map": shared_map,
            })
            step = env.step({"a": result["action"]})
            observations = step["observations"]

        final_records = session.visible_records("a", kind="agent_update")
        final_map = _build_shared_map(final_records)
        self.assertGreater(
            len(final_map["cells"]), 0,
            "Shared map should contain discovered cells after multiple rounds",
        )

    def test_action_is_valid_integer(self):
        """Actions produced by policies must be valid integers the env accepts."""
        session, env, agents = self._make_session_and_agents(["a"])
        observations = env.reset(seed=42)

        for round_id in range(1, 4):
            shared_records = session.visible_records("a", kind="agent_update")
            shared_map = _build_shared_map(shared_records)
            result = agents["a"].decide(observations["a"], round_id, inputs={
                "observation": observations["a"],
                "shared_map": shared_map,
            })
            action = result["action"]
            self.assertIsInstance(action, int, f"Action should be int, got {type(action)}")
            self.assertIn(action, {0, 1, 2, 3, 4}, f"Action {action} not in valid set")
            step = env.step({"a": action})
            observations = step["observations"]

    def test_records_have_correct_structure(self):
        """agent_update records must contain local_knowledge with observation that has cells."""
        session, env, agents = self._make_session_and_agents(["a"])
        observations = env.reset(seed=42)
        shared_map = _build_shared_map([])
        agents["a"].decide(observations["a"], 1, inputs={
            "observation": observations["a"],
            "shared_map": shared_map,
        })

        records = session.inspect("agent_update")
        self.assertEqual(len(records), 1)
        payload = records[0].payload
        self.assertIn("local_knowledge", payload)
        lk = payload["local_knowledge"]
        self.assertIn("observation", lk)
        self.assertIn("cells", lk["observation"])
        self.assertGreater(len(lk["observation"]["cells"]), 0)

    def test_peer_to_peer_topology_filters_records(self):
        """In P2P, agent sees only own + visible peers' records, not all agents."""
        session, env, agents = self._make_session_and_agents(
            ["a", "b", "c"],
            topology_mode="peer_to_peer",
            visibility={"a": ["b"]},
        )
        observations = env.reset(seed=42)

        for round_id in range(1, 4):
            actions = {}
            for aid, agent in agents.items():
                shared_records = session.visible_records(aid, kind="agent_update")
                shared_map = _build_shared_map(shared_records)
                result = agent.decide(observations.get(aid, {}), round_id, inputs={
                    "observation": observations.get(aid, {}),
                    "shared_map": shared_map,
                })
                actions[aid] = result["action"]
            step = env.step(actions)
            observations = step["observations"]

        records_a = session.visible_records("a", kind="agent_update")
        records_c = session.visible_records("c", kind="agent_update")

        actors_visible_to_a = {r.actor for r in records_a}
        actors_visible_to_c = {r.actor for r in records_c}

        self.assertIn("a", actors_visible_to_a)
        self.assertIn("b", actors_visible_to_a)
        self.assertNotIn("c", actors_visible_to_a)

        self.assertIn("c", actors_visible_to_c)
        self.assertNotIn("a", actors_visible_to_c)
        self.assertNotIn("b", actors_visible_to_c)

    def test_coverage_increases_over_rounds(self):
        """Running the loop should discover new cells over time."""
        session, env, agents = self._make_session_and_agents(["a", "b"])
        observations = env.reset(seed=42)
        discovered: set[Tuple[int, int]] = set()
        for obs in observations.values():
            for cell in obs.get("cells", []):
                discovered.add((cell["x"], cell["y"]))

        initial_count = len(discovered)

        for round_id in range(1, 21):
            actions = {}
            for aid, agent in agents.items():
                shared_records = session.visible_records(aid, kind="agent_update")
                shared_map = _build_shared_map(shared_records)
                result = agent.decide(observations.get(aid, {}), round_id, inputs={
                    "observation": observations.get(aid, {}),
                    "shared_map": shared_map,
                })
                actions[aid] = result["action"]
            step = env.step(actions)
            observations = step["observations"]
            for obs in observations.values():
                for cell in obs.get("cells", []):
                    discovered.add((cell["x"], cell["y"]))

        self.assertGreater(
            len(discovered), initial_count,
            "Coverage should increase after 20 rounds of exploration",
        )

    def test_inspect_returns_records(self):
        """session.inspect() should return records after a run."""
        session, env, agents = self._make_session_and_agents(["a"])
        observations = env.reset(seed=42)

        for round_id in range(1, 4):
            shared_records = session.visible_records("a", kind="agent_update")
            shared_map = _build_shared_map(shared_records)
            result = agents["a"].decide(observations["a"], round_id, inputs={
                "observation": observations["a"],
                "shared_map": shared_map,
            })
            step = env.step({"a": result["action"]})
            observations = step["observations"]

        agent_updates = session.inspect("agent_update")
        outcomes = session.inspect("outcome")
        traces = session.inspect("trace")

        self.assertEqual(len(agent_updates), 3)
        self.assertEqual(len(outcomes), 3)
        self.assertEqual(len(traces), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
