"""Tests for participation registry."""

import unittest

from doagent.core import InMemoryParticipationRegistry, ParticipationRecord


class TestParticipationRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = InMemoryParticipationRegistry()

    def test_register_and_get(self) -> None:
        """Ensure register stores records and get retrieves them."""
        record = ParticipationRecord(
            agent_id="agent-1",
            capabilities=["compute"],
            resource_limits={"cpu": 2.0},
        )
        self.registry.register(record)
        self.assertEqual(self.registry.get("agent-1"), record)

    def test_update(self) -> None:
        """Ensure update replaces an existing record."""
        record = ParticipationRecord(agent_id="agent-1", capabilities=["compute"])
        self.registry.register(record)

        updated = ParticipationRecord(agent_id="agent-1", capabilities=["compute", "search"])
        self.registry.update(updated)
        self.assertEqual(self.registry.get("agent-1"), updated)

    def test_deregister(self) -> None:
        """Ensure deregister removes a record."""
        record = ParticipationRecord(agent_id="agent-1", capabilities=["compute"])
        self.registry.register(record)
        self.registry.deregister("agent-1")
        self.assertIsNone(self.registry.get("agent-1"))

    def test_list(self) -> None:
        """Ensure list returns all records."""
        record_a = ParticipationRecord(agent_id="a", capabilities=["compute"])
        record_b = ParticipationRecord(agent_id="b", capabilities=["search"])
        self.registry.register(record_a)
        self.registry.register(record_b)
        self.assertEqual(list(self.registry.list()), [record_a, record_b])


if __name__ == "__main__":
    unittest.main(verbosity=2)
