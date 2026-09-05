"""Tests for topology configuration and routing."""

import unittest

from doagent.core import RoutingDecision, Topology, TopologyConfig, select_routing
from doagent.core.topology import (
    make_default_membership_hook,
    mesh_on_membership_change,
    relay_join_leave_as_hub,
    snapshot_hub_roster,
)


class TestTopology(unittest.TestCase):
    def test_default_topology(self) -> None:
        """Ensure default topology is centralised."""
        config = TopologyConfig()
        self.assertEqual(config.mode, Topology.CENTRALISED)

    def test_select_routing_centralised(self) -> None:
        """Ensure routing decision matches centralised mode."""
        config = TopologyConfig(mode=Topology.CENTRALISED)
        decision = select_routing(config)
        self.assertIsInstance(decision, RoutingDecision)
        self.assertEqual(decision.mode, Topology.CENTRALISED)

    def test_select_routing_federated(self) -> None:
        """Ensure routing decision matches federated mode."""
        config = TopologyConfig(mode=Topology.FEDERATED)
        decision = select_routing(config)
        self.assertEqual(decision.mode, Topology.FEDERATED)

    def test_select_routing_peer_to_peer(self) -> None:
        """Ensure routing decision matches peer-to-peer mode."""
        config = TopologyConfig(mode=Topology.PEER_TO_PEER)
        decision = select_routing(config)
        self.assertEqual(decision.mode, Topology.PEER_TO_PEER)

    def test_mesh_on_join_links_newcomer_both_ways(self) -> None:
        vis = mesh_on_membership_change(
            "join", "c", ["a", "b", "c"], {"a": ["b"]},
        )
        self.assertCountEqual(vis["a"], ["b", "c"])
        self.assertCountEqual(vis["b"], ["c"])
        self.assertCountEqual(vis["c"], ["a", "b"])

    def test_mesh_on_leave_removes_from_every_list(self) -> None:
        vis = mesh_on_membership_change(
            "leave", "c", ["a", "b"],
            {"a": ["b", "c"], "b": ["a", "c"], "c": ["a", "b"]},
        )
        self.assertNotIn("c", vis)
        self.assertEqual(vis["a"], ["b"])
        self.assertEqual(vis["b"], ["a"])

    def test_default_hook_keeps_yaml_for_listed_agents(self) -> None:
        hook = make_default_membership_hook({"a": ["b"]})
        vis = {"a": ["b"]}
        vis = hook("join", "a", ["a"], vis)
        vis = hook("join", "b", ["a", "b"], vis)
        self.assertEqual(vis["a"], ["b"])
        self.assertEqual(vis.get("b", []), [])

    def test_default_hook_meshes_unlisted_agent(self) -> None:
        hook = make_default_membership_hook({"a": ["b"]})
        vis = {"a": ["b"]}
        vis = hook("join", "a", ["a"], vis)
        vis = hook("join", "b", ["a", "b"], vis)
        vis = hook("join", "c", ["a", "b", "c"], vis)
        self.assertCountEqual(vis["a"], ["b", "c"])
        self.assertCountEqual(vis["b"], ["c"])
        self.assertCountEqual(vis["c"], ["a", "b"])

    def test_snapshot_hub_roster_writes_one_roster(self) -> None:
        writes = snapshot_hub_roster(
            "join", "a",
            [{"agent_id": "a", "capabilities": ["map"], "resource_limits": {}}],
            "hub",
        )
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0]["event"], "roster")
        self.assertEqual(writes[0]["actor"], "hub")
        self.assertEqual(writes[0]["members"][0]["agent_id"], "a")

    def test_relay_join_leave_as_hub_sets_member_id(self) -> None:
        writes = relay_join_leave_as_hub(
            "join", "a",
            [{"agent_id": "a", "capabilities": ["map"], "resource_limits": {}}],
            "hub",
        )
        self.assertEqual(writes[0]["event"], "join")
        self.assertEqual(writes[0]["actor"], "hub")
        self.assertEqual(writes[0]["member_id"], "a")
        self.assertEqual(writes[0]["capabilities"], ["map"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
