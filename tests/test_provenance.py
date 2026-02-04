"""Tests for provenance helper and record round-trip."""

import unittest

from doagent.core import InMemorySharedData, new_record
from doagent.records import SimpleRecord, new_provenance


class TestProvenanceHelper(unittest.TestCase):
    def setUp(self) -> None:
        self.shared_data = InMemorySharedData()

    def test_new_provenance_builds_one_contribution(self) -> None:
        """Ensure new_provenance returns a structure with one contribution."""
        p = new_provenance(
            agent="agent-1",
            sources=["r1", "r2"],
            tools=["search"],
            notes="Initial creation",
        )
        self.assertIn("contributions", p)
        self.assertEqual(len(p["contributions"]), 1)
        c = p["contributions"][0]
        self.assertEqual(c["agent"], "agent-1")
        self.assertEqual(c["sources"], ["r1", "r2"])
        self.assertEqual(c["tools"], ["search"])
        self.assertEqual(c["notes"], "Initial creation")

    def test_record_round_trip_with_provenance_from_helper(self) -> None:
        """Ensure record created with provenance via helper round-trips."""
        provenance = new_provenance(
            agent="agent-1",
            sources=["r1"],
            tools=["t1"],
        )
        record = new_record(
            actor="agent-1",
            kind="note",
            payload={"text": "hello"},
            provenance=provenance,
        )
        self.shared_data.write(record)

        fetched = self.shared_data.read(record.id)
        self.assertIsInstance(fetched, SimpleRecord)
        self.assertEqual(fetched, record)
        self.assertEqual(len(fetched.provenance.get("contributions", [])), 1)
        self.assertEqual(fetched.provenance["contributions"][0]["agent"], "agent-1")
        self.assertEqual(fetched.provenance["contributions"][0]["sources"], ["r1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
