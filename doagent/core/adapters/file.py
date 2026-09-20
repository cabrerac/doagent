"""File-backed shared data that keeps records in memory and writes them on flush.

Each record kind becomes one JSONL file in the given directory.
Reads and writes use memory during a run.
flush writes every kind file once.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from ...interface.shared_data import SharedDataAdapter
from ...records import SimpleRecord


class FileSharedData(SharedDataAdapter):
    """Shared data adapter that keeps records in memory and persists on flush.

    Opening an existing directory loads its JSONL files into memory.
    """

    def __init__(self, directory: str | Path) -> None:
        """Initialise the adapter with a directory path.

        Args:
            directory:
                Directory where kind files are stored.
                Created on the first flush if it does not exist.
        """
        self._dir = Path(directory)
        self._collections: Dict[str, Dict[str, SimpleRecord]] = {}
        self._insertion_order: list[str] = []
        self._id_to_kind: Dict[str, str] = {}
        self._state_index: Dict[str, str] = {}
        self._dirty = False
        self._load()

    def _kind_path(self, kind: str) -> Path:
        """Return the JSONL path for one record kind.

        Args:
            kind:
                Record kind name.

        Returns:
            Path of that kind file under the adapter directory.
        """
        return self._dir / f"{kind}.jsonl"

    def _store(self, record: SimpleRecord) -> None:
        """Add a record to the in-memory collections.

        Args:
            record:
                Record to store.
        """
        kind = record.kind
        if kind not in self._collections:
            self._collections[kind] = {}
        self._collections[kind][record.id] = record
        self._insertion_order.append(record.id)
        self._id_to_kind[record.id] = kind

    def _load(self) -> None:
        """Load existing JSONL files from the directory into memory."""
        if not self._dir.exists():
            return
        loaded: List[SimpleRecord] = []
        for path in self._dir.glob("*.jsonl"):
            loaded.extend(self._read_file(path))
        loaded.sort(key=lambda record: record.timestamp)
        for record in loaded:
            self._store(record)
        self._dirty = False

    def write(self, record: SimpleRecord) -> None:
        """Store a record in memory.

        Args:
            record:
                Record to keep until flush.
        """
        self._store(record)
        self._dirty = True

    def flush(self) -> None:
        """Write the in-memory records to one JSONL file per kind."""
        if not self._dirty:
            return
        self._dir.mkdir(parents=True, exist_ok=True)
        by_kind: Dict[str, List[SimpleRecord]] = {}
        for record_id in self._insertion_order:
            kind = self._id_to_kind.get(record_id)
            if kind is None:
                continue
            record = self._collections.get(kind, {}).get(record_id)
            if record is None:
                continue
            by_kind.setdefault(kind, []).append(record)
        for kind, records in by_kind.items():
            path = self._kind_path(kind)
            with path.open("w", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        self._dirty = False

    def read(self, record_id: str) -> Optional[SimpleRecord]:
        """Return a record by id if it is in memory.

        Args:
            record_id:
                Record id to look up.

        Returns:
            The record, or None if it is not stored.
        """
        kind = self._id_to_kind.get(record_id)
        if kind is None:
            return None
        return self._collections.get(kind, {}).get(record_id)

    def list(self) -> Iterable[SimpleRecord]:
        """Return records in insertion order.

        Returns:
            Every stored record.
        """
        results: List[SimpleRecord] = []
        for record_id in self._insertion_order:
            kind = self._id_to_kind.get(record_id)
            if kind is None:
                continue
            record = self._collections.get(kind, {}).get(record_id)
            if record is not None:
                results.append(record)
        return results

    def listen(
        self,
        kind: str,
        *,
        actor: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> Iterable[SimpleRecord]:
        """Yield records of one kind that match the optional filters.

        Args:
            kind:
                Record kind to select.
            actor:
                If set, keep only this actor.
            since:
                If set, keep records at or after this timestamp.
            until:
                If set, keep records at or before this timestamp.

        Returns:
            Matching records from memory.
        """
        records = list(self._collections.get(kind, {}).values())
        if actor is not None:
            records = [record for record in records if record.actor == actor]
        if since is not None:
            records = [record for record in records if record.timestamp >= since]
        if until is not None:
            records = [record for record in records if record.timestamp <= until]
        return records

    def lookup_outcome_by_hash(self, state_hash: str) -> Optional[str]:
        """Return the outcome id for an already-seen state hash.

        Args:
            state_hash:
                Hash of an environment state.

        Returns:
            The stored outcome id, or None if this state has not been seen.
        """
        return self._state_index.get(state_hash)

    def index_outcome(self, state_hash: str, outcome_id: str) -> None:
        """Remember the outcome id for a state hash.

        Args:
            state_hash:
                Hash of an environment state.
            outcome_id:
                Id of the outcome record that produced that state.
        """
        self._state_index[state_hash] = outcome_id

    @staticmethod
    def _read_file(path: Path) -> List[SimpleRecord]:
        """Read one JSONL file into record objects.

        Args:
            path:
                File to read.

        Returns:
            Records from that file, in file order.
        """
        records: List[SimpleRecord] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                data = json.loads(line)
                data.setdefault("accountability", {})
                records.append(SimpleRecord(**data))
        return records
