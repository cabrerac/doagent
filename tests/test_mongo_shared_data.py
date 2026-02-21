"""Tests for MongoSharedData adapter using mongomock."""

import unittest

try:
    import mongomock

    HAS_MONGOMOCK = True
except ImportError:
    HAS_MONGOMOCK = False

from doagent.core import new_record
from doagent.core.mongo_shared_data import MongoSharedData
from doagent.records import SimpleRecord


@unittest.skipUnless(HAS_MONGOMOCK, "mongomock not installed")
class TestMongoSharedData(unittest.TestCase):
    def setUp(self):
        self.client = mongomock.MongoClient()
        self.db = self.client["test_doagent"]
        self.adapter = MongoSharedData(self.db)

    def tearDown(self):
        self.client.close()

    def test_write_read_round_trip(self):
        record = new_record(actor="agent-1", kind="note", payload={"text": "hello"})
        self.adapter.write(record)
        fetched = self.adapter.read(record.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, record.id)
        self.assertEqual(fetched.payload, record.payload)

    def test_list_returns_all_records(self):
        r1 = new_record(actor="agent-1", kind="agent_update", payload={"n": 1})
        r2 = new_record(actor="agent-2", kind="outcome", payload={"n": 2})
        self.adapter.write(r1)
        self.adapter.write(r2)
        records = list(self.adapter.list())
        self.assertEqual(len(records), 2)
        record_ids = {r.id for r in records}
        self.assertIn(r1.id, record_ids)
        self.assertIn(r2.id, record_ids)

    def test_listen_filters_by_kind(self):
        note = new_record(actor="agent-1", kind="note", payload={"n": 1})
        task = new_record(actor="agent-2", kind="task", payload={"n": 2})
        self.adapter.write(note)
        self.adapter.write(task)
        records = list(self.adapter.listen("note"))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].id, note.id)

    def test_listen_filters_by_actor(self):
        r1 = new_record(actor="agent-1", kind="note", payload={"n": 1})
        r2 = new_record(actor="agent-2", kind="note", payload={"n": 2})
        self.adapter.write(r1)
        self.adapter.write(r2)
        records = list(self.adapter.listen("note", actor="agent-2"))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].id, r2.id)

    def test_records_stored_in_kind_collections(self):
        """Each kind maps to its own MongoDB collection."""
        r1 = new_record(actor="a", kind="agent_update", payload={})
        r2 = new_record(actor="b", kind="outcome", payload={})
        r3 = new_record(actor="c", kind="trace", payload={})
        self.adapter.write(r1)
        self.adapter.write(r2)
        self.adapter.write(r3)

        self.assertEqual(self.db["agent_update"].count_documents({}), 1)
        self.assertEqual(self.db["outcome"].count_documents({}), 1)
        self.assertEqual(self.db["trace"].count_documents({}), 1)

    def test_dedup_index_lookup_and_store(self):
        self.assertIsNone(self.adapter.lookup_outcome_by_hash("abc123"))
        self.adapter.index_outcome("abc123", "outcome-001")
        self.assertEqual(self.adapter.lookup_outcome_by_hash("abc123"), "outcome-001")

    def test_dedup_index_upsert(self):
        self.adapter.index_outcome("hash1", "id-old")
        self.adapter.index_outcome("hash1", "id-new")
        self.assertEqual(self.adapter.lookup_outcome_by_hash("hash1"), "id-new")

    def test_ensure_indexes_no_error(self):
        self.adapter.ensure_indexes()

    def test_read_unknown_id_returns_none(self):
        self.assertIsNone(self.adapter.read("nonexistent"))

    def test_state_index_not_in_list(self):
        """Internal _state_index collection should not appear in list()."""
        r1 = new_record(actor="a", kind="note", payload={})
        self.adapter.write(r1)
        self.adapter.index_outcome("hash1", "id1")
        records = list(self.adapter.list())
        self.assertEqual(len(records), 1)


@unittest.skipUnless(HAS_MONGOMOCK, "mongomock not installed")
class TestMongoAdapterParity(unittest.TestCase):
    """Verify MongoSharedData produces the same results as InMemorySharedData."""

    def test_parity_with_inmemory(self):
        from doagent.core import InMemorySharedData

        mem = InMemorySharedData()
        client = mongomock.MongoClient()
        mongo = MongoSharedData(client["parity_test"])

        records = [
            new_record(actor="a", kind="agent_update", payload={"x": 1}),
            new_record(actor="b", kind="outcome", payload={"y": 2}),
            new_record(actor="a", kind="agent_update", payload={"x": 3}),
        ]
        for r in records:
            mem.write(r)
            mongo.write(r)

        mem_notes = list(mem.listen("agent_update"))
        mongo_notes = list(mongo.listen("agent_update"))
        self.assertEqual(len(mem_notes), len(mongo_notes))
        self.assertEqual(
            {r.id for r in mem_notes},
            {r.id for r in mongo_notes},
        )

        mem_all = list(mem.list())
        mongo_all = list(mongo.list())
        self.assertEqual(len(mem_all), len(mongo_all))

        client.close()


if __name__ == "__main__":
    unittest.main()
