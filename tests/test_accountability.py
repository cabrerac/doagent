"""Tests for accountability helper and record round-trip."""

import unittest

from doagent.core import InMemorySharedData, new_record
from doagent.records import SimpleRecord, new_accountability


class TestAccountabilityHelper(unittest.TestCase):
    def setUp(self) -> None:
        self.shared_data = InMemorySharedData()

    def test_new_accountability_builds_dict(self) -> None:
        """Ensure new_accountability returns a structure with optional fields."""
        a = new_accountability(
            owner="team-a",
            policy_id="policy-001",
            responsibility_scope="decisions",
        )
        self.assertEqual(a["owner"], "team-a")
        self.assertEqual(a["policy_id"], "policy-001")
        self.assertEqual(a["responsibility_scope"], "decisions")

    def test_new_accountability_partial(self) -> None:
        """Ensure new_accountability accepts partial fields."""
        a = new_accountability(owner="team-b")
        self.assertEqual(a["owner"], "team-b")
        self.assertNotIn("policy_id", a)
        self.assertNotIn("responsibility_scope", a)

    def test_record_round_trip_with_accountability(self) -> None:
        """Ensure record created with accountability via helper round-trips."""
        accountability = new_accountability(
            owner="team-a",
            policy_id="policy-001",
            responsibility_scope="decisions",
        )
        record = new_record(
            actor="agent-1",
            kind="decision",
            payload={"decision": {"action": "approve"}},
            accountability=accountability,
        )
        self.shared_data.write(record)

        fetched = self.shared_data.read(record.id)
        self.assertIsInstance(fetched, SimpleRecord)
        self.assertEqual(fetched, record)
        self.assertEqual(fetched.accountability["owner"], "team-a")
        self.assertEqual(fetched.accountability["policy_id"], "policy-001")
        self.assertEqual(fetched.accountability["responsibility_scope"], "decisions")

    def test_record_without_accountability_has_empty_dict(self) -> None:
        """Ensure record created without accountability has empty dict (backward compat)."""
        record = new_record(
            actor="agent-1",
            kind="note",
            payload={"text": "hello"},
        )
        self.assertEqual(record.accountability, {})
        self.shared_data.write(record)
        fetched = self.shared_data.read(record.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.accountability, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
