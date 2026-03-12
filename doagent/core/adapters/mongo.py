"""MongoDB shared data adapter: one collection per record kind.

Requires ``pymongo``::

    pip install pymongo

Usage::

    from pymongo import MongoClient
    from doagent.core.adapters import MongoSharedData

    client = MongoClient("mongodb://localhost:27017")
    shared_data = MongoSharedData(client["doagent_run_001"])
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Optional

from ...interface.shared_data import SharedDataAdapter
from ...records import SimpleRecord

_STATE_INDEX_COLLECTION = "_state_index"


class MongoSharedData(SharedDataAdapter):
    """MongoDB adapter using one collection per record kind.

    Each record kind maps to a MongoDB collection. The dedup state
    index lives in a ``_state_index`` collection with unique hash keys.
    """

    def __init__(self, db: Any) -> None:
        """Initialise with a pymongo Database instance.

        Args:
            db: A ``pymongo.database.Database`` object. The adapter
                creates collections on first write.
        """
        self._db = db

    def write(self, record: SimpleRecord) -> None:
        """Insert a record into its kind's collection."""
        collection = self._db[record.kind]
        doc = asdict(record)
        doc["_record_id"] = doc["id"]
        collection.insert_one(doc)

    def read(self, record_id: str) -> Optional[SimpleRecord]:
        """Return a record by id, scanning all collections."""
        for name in self._db.list_collection_names():
            if name.startswith("_"):
                continue
            doc = self._db[name].find_one({"_record_id": record_id})
            if doc is not None:
                return self._doc_to_record(doc)
        return None

    def list(self) -> Iterable[SimpleRecord]:
        """Return all records across collections, sorted by timestamp."""
        records: List[SimpleRecord] = []
        for name in self._db.list_collection_names():
            if name.startswith("_"):
                continue
            for doc in self._db[name].find():
                records.append(self._doc_to_record(doc))
        records.sort(key=lambda r: r.timestamp)
        return records

    def listen(
        self,
        kind: str,
        *,
        actor: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> Iterable[SimpleRecord]:
        """Query the kind's collection with optional filters."""
        query: Dict[str, Any] = {}
        if actor is not None:
            query["actor"] = actor
        ts_filter: Dict[str, str] = {}
        if since is not None:
            ts_filter["$gte"] = since
        if until is not None:
            ts_filter["$lte"] = until
        if ts_filter:
            query["timestamp"] = ts_filter

        return [
            self._doc_to_record(doc)
            for doc in self._db[kind].find(query)
        ]

    def lookup_outcome_by_hash(self, state_hash: str) -> Optional[str]:
        """Return outcome id for an already-seen state hash, or None."""
        doc = self._db[_STATE_INDEX_COLLECTION].find_one(
            {"state_hash": state_hash},
        )
        if doc is not None:
            return doc["outcome_id"]
        return None

    def index_outcome(self, state_hash: str, outcome_id: str) -> None:
        """Upsert state_hash -> outcome_id mapping."""
        self._db[_STATE_INDEX_COLLECTION].update_one(
            {"state_hash": state_hash},
            {"$set": {"outcome_id": outcome_id}},
            upsert=True,
        )

    def ensure_indexes(self) -> None:
        """Create recommended MongoDB indexes for query performance.

        Call once after creating the adapter to ensure fast lookups.
        Not called automatically to avoid index creation on every
        instantiation.
        """
        for kind in ("agent_update", "outcome", "trace"):
            col = self._db[kind]
            col.create_index("_record_id", unique=True, sparse=True)
            col.create_index("actor")
            col.create_index("timestamp")
        self._db[_STATE_INDEX_COLLECTION].create_index(
            "state_hash", unique=True,
        )

    @staticmethod
    def _doc_to_record(doc: Dict[str, Any]) -> SimpleRecord:
        doc.pop("_id", None)
        doc.pop("_record_id", None)
        doc.setdefault("accountability", {})
        return SimpleRecord(**doc)
