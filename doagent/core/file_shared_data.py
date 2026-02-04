"""File-based shared data adapter."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Optional

from ..interface.shared_data import SharedDataAdapter
from ..records import SimpleRecord


class FileSharedData(SharedDataAdapter):
    """Append-only file adapter using JSON lines."""

    def __init__(self, path: str | Path) -> None:
        """Initialise the adapter with a file path."""
        self._path = Path(path)

    def write(self, record: SimpleRecord) -> None:
        """Append a record as JSON to the file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")

    def read(self, record_id: str) -> Optional[SimpleRecord]:
        """Return a record by id if present."""
        for record in self.list():
            if record.id == record_id:
                return record
        return None

    def list(self) -> Iterable[SimpleRecord]:
        """Return records in file order."""
        if not self._path.exists():
            return []
        records: list[SimpleRecord] = []
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                payload = json.loads(line)
                payload.setdefault("accountability", {})
                records.append(SimpleRecord(**payload))
        return records

    def listen(
        self,
        kind: str,
        *,
        actor: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> Iterable[SimpleRecord]:
        """Yield records matching a kind with optional filters."""
        records = [record for record in self.list() if record.kind == kind]

        if actor is not None:
            records = [record for record in records if record.actor == actor]

        if since is not None:
            records = [record for record in records if record.timestamp >= since]

        if until is not None:
            records = [record for record in records if record.timestamp <= until]

        return records
