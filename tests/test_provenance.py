"""Tests for provenance helper and record round-trip."""

import unittest

from doagent.core import InMemorySharedData, new_record
from doagent.records import SimpleRecord, new_provenance


class TestProvenanceHelper(unittest.TestCase):
    def setUp(self) -> None:
        self.shared_data = InMemorySharedData()

    def test_new_provenance_builds_flat_attribution(self) -> None:
        """Ensure new_provenance returns a flat attribution dict."""
        p = new_provenance(
            agent="agent-1",
            sources=["r1", "r2"],
            tools=["search"],
            notes="Initial creation",
        )
        self.assertEqual(p["created_by"], "agent-1")
        self.assertEqual(p["derived_from"], ["r1", "r2"])
        self.assertEqual(p["used_tools"], ["search"])
        self.assertEqual(p["notes"], "Initial creation")

    def test_new_provenance_minimal(self) -> None:
        """Ensure minimal provenance only contains created_by."""
        p = new_provenance(agent="agent-1")
        self.assertEqual(p, {"created_by": "agent-1"})
        self.assertNotIn("derived_from", p)
        self.assertNotIn("used_tools", p)

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
        self.assertEqual(fetched.provenance["created_by"], "agent-1")
        self.assertEqual(fetched.provenance["derived_from"], ["r1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
