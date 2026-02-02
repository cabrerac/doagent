"""Tests for agent adapter behaviour."""

import unittest

from doagent.core import InMemorySharedData, StubAgent


class TestStubAgent(unittest.TestCase):
    def setUp(self) -> None:
        self.shared_data = InMemorySharedData()
        self.agent = StubAgent("agent-1", self.shared_data)

    def test_write_and_read(self) -> None:
        """Ensure stub agent write/read round-trip works."""
        record = self.agent.write(kind="note", payload={"text": "hello"})

        fetched = self.agent.read(record.id)
        self.assertEqual(fetched, record)

    def test_listen_by_kind(self) -> None:
        """Ensure stub agent listen filters by kind."""
        note = self.agent.write(kind="note", payload={"text": "hello"})
        self.agent.write(kind="task", payload={"text": "todo"})

        records = list(self.agent.listen("note"))
        self.assertEqual(records, [note])


if __name__ == "__main__":
    unittest.main(verbosity=2)
