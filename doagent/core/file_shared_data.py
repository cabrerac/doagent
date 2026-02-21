"""File-based shared data adapter using one JSONL file per record kind.

Storage layout mirrors MongoDB collections and InMemorySharedData:

    <directory>/
        agent_update.jsonl
        outcome.jsonl
        trace.jsonl
        ...
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from ..interface.shared_data import SharedDataAdapter
from ..records import SimpleRecord


class FileSharedData(SharedDataAdapter):
    """Append-only file adapter using one JSONL file per record kind.

    Each kind (agent_update, outcome, trace, ...) is stored in its own
    ``<kind>.jsonl`` file inside the given directory. This makes
    kind-scoped queries (``listen``) efficient and aligns the on-disk
    layout with how MongoDB and the in-memory adapter organise data.
    """

    def __init__(self, directory: str | Path) -> None:
        """Initialise the adapter with a directory path.

        Args:
            directory: Directory where ``<kind>.jsonl`` files are stored.
                Created on first write if it does not exist.
        """
        self._dir = Path(directory)
        self._state_index: Dict[str, str] = {}

    def _kind_path(self, kind: str) -> Path:
        return self._dir / f"{kind}.jsonl"

    def write(self, record: SimpleRecord) -> None:
        """Append a record to its kind's JSONL file."""
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._kind_path(record.kind)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")

    def read(self, record_id: str) -> Optional[SimpleRecord]:
        """Return a record by id, scanning all kind files."""
        if not self._dir.exists():
            return None
        for path in self._dir.glob("*.jsonl"):
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    data = json.loads(line)
                    if data.get("id") == record_id:
                        data.setdefault("accountability", {})
                        return SimpleRecord(**data)
        return None

    def list(self) -> Iterable[SimpleRecord]:
        """Return all records across kinds, sorted by timestamp."""
        if not self._dir.exists():
            return []
        records: List[SimpleRecord] = []
        for path in self._dir.glob("*.jsonl"):
            records.extend(self._read_file(path))
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
        """Yield records from the kind's file with optional filters."""
        path = self._kind_path(kind)
        if not path.exists():
            return []
        records = self._read_file(path)

        if actor is not None:
            records = [r for r in records if r.actor == actor]

        if since is not None:
            records = [r for r in records if r.timestamp >= since]

        if until is not None:
            records = [r for r in records if r.timestamp <= until]

        return records

    def lookup_outcome_by_hash(self, state_hash: str) -> Optional[str]:
        """Return outcome id for an already-seen state hash, or None."""
        return self._state_index.get(state_hash)

    def index_outcome(self, state_hash: str, outcome_id: str) -> None:
        """Store state_hash -> outcome_id mapping."""
        self._state_index[state_hash] = outcome_id

    @staticmethod
    def _read_file(path: Path) -> List[SimpleRecord]:
        records: List[SimpleRecord] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                data = json.loads(line)
                data.setdefault("accountability", {})
                records.append(SimpleRecord(**data))
        return records
