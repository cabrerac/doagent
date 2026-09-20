"""Tests for shared data adapters and records."""

import tempfile
import unittest
from pathlib import Path

from doagent.core import FileSharedData, InMemorySharedData, new_record
from doagent.records import SimpleRecord


class TestSharedData(unittest.TestCase):
    def setUp(self) -> None:
        self.shared_data = InMemorySharedData()

    def test_write_read_round_trip(self) -> None:
        """Ensure write/read round-trip preserves the record."""
        record = new_record(
            actor="agent-1",
            kind="note",
            payload={"text": "hello"},
            provenance={
                "created_by": "agent-1",
                "derived_from": ["r1"],
                "used_tools": ["t1"],
            },
        )
        self.shared_data.write(record)

        fetched = self.shared_data.read(record.id)
        self.assertIsInstance(fetched, SimpleRecord)
        self.assertEqual(fetched, record)

    def test_list_returns_records(self) -> None:
        """Ensure list returns records in insertion order."""
        first = new_record(actor="agent-1", kind="note", payload={"n": 1})
        second = new_record(actor="agent-2", kind="note", payload={"n": 2})
        self.shared_data.write(first)
        self.shared_data.write(second)

        records = list(self.shared_data.list())
        self.assertEqual(records, [first, second])

    def test_listen_filters_by_kind(self) -> None:
        """Ensure listen filters records by kind."""
        note = new_record(actor="agent-1", kind="note", payload={"n": 1})
        task = new_record(actor="agent-2", kind="task", payload={"n": 2})
        self.shared_data.write(note)
        self.shared_data.write(task)

        records = list(self.shared_data.listen("note"))
        self.assertEqual(records, [note])

    def test_listen_filters_by_actor(self) -> None:
        """Ensure listen filters records by actor."""
        note_a = new_record(actor="agent-1", kind="note", payload={"n": 1})
        note_b = new_record(actor="agent-2", kind="note", payload={"n": 2})
        self.shared_data.write(note_a)
        self.shared_data.write(note_b)

        records = list(self.shared_data.listen("note", actor="agent-2"))
        self.assertEqual(records, [note_b])

    def test_file_adapter_parity(self) -> None:
        """Ensure file adapter parity with in-memory adapter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_adapter = FileSharedData(temp_dir)

            first = new_record(
                actor="agent-1",
                kind="note",
                payload={"n": 1},
                provenance={
                    "created_by": "agent-1",
                    "derived_from": ["r1"],
                    "used_tools": ["t1"],
                },
            )
            second = new_record(actor="agent-2", kind="note", payload={"n": 2})
            self.shared_data.write(first)
            self.shared_data.write(second)

            file_adapter.write(first)
            file_adapter.write(second)

            self.assertEqual(list(self.shared_data.list()), list(file_adapter.list()))
            self.assertEqual(
                list(self.shared_data.listen("note")),
                list(file_adapter.listen("note")),
            )

            file_round_trip = file_adapter.read(first.id)
            self.assertIsNotNone(file_round_trip)
            self.assertEqual(file_round_trip, first)

    def test_file_adapter_writes_disk_on_flush(self) -> None:
        """Writes stay in memory until flush, then reload from disk."""
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = FileSharedData(temp_dir)
            record = new_record(actor="agent-1", kind="note", payload={"n": 1})
            adapter.write(record)
            path = Path(temp_dir) / "note.jsonl"
            self.assertFalse(path.exists())
            self.assertEqual(adapter.read(record.id), record)
            adapter.flush()
            self.assertTrue(path.is_file())
            reloaded = FileSharedData(temp_dir)
            self.assertEqual(reloaded.read(record.id), record)
            self.assertEqual(list(reloaded.list()), [record])


if __name__ == "__main__":
    unittest.main(verbosity=2)
