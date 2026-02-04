"""Tests for topology configuration and routing."""

import unittest

from doagent.core import RoutingDecision, Topology, TopologyConfig, select_routing


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
