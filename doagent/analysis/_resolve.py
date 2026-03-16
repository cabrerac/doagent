"""Internal run resolution: load run metadata and expose inspect-style access to records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

from ..core.adapters.file import FileSharedData
from ..records import SimpleRecord


def _get_mongo_shared_data_class() -> Any:
    """Lazy import of MongoSharedData so pymongo is only required when resolving mongo runs."""
    try:
        from ..core.adapters import MongoSharedData
        return MongoSharedData
    except ImportError as e:
        raise ImportError(
            "Analysis for storage_type 'mongo' requires pymongo. pip install pymongo"
        ) from e


def _load_metadata(run_id: str, output_base: str | Path = "./output") -> dict[str, Any]:
    """Read metadata.json for a run. Raises FileNotFoundError if run folder or metadata missing."""
    base = Path(output_base)
    meta_path = base / run_id / "metadata.json"
    if not meta_path.is_file():
        raise FileNotFoundError(f"Run metadata not found: {meta_path}")
    with meta_path.open("r", encoding="utf-8") as f:
        return json.load(f)


class _ResolvedRun:
    """Read-only view of a run's records, with inspect(kind) like Session."""

    def __init__(self, run_id: str, metadata: dict[str, Any], output_base: Path) -> None:
        self._run_id = run_id
        self._metadata = metadata
        self._output_base = output_base
        self._adapter: Optional[Any] = None

    def _get_adapter(self) -> Any:
        if self._adapter is not None:
            return self._adapter
        storage = (self._metadata.get("storage_type") or "file").lower()
        if storage == "file":
            records_dir = self._metadata.get("records_dir", "records")
            records_path = self._output_base / self._run_id / records_dir
            if not records_path.is_dir():
                raise FileNotFoundError(f"Records directory not found: {records_path}")
            self._adapter = FileSharedData(records_path)
            return self._adapter
        if storage == "mongo":
            mongo_uri = self._metadata.get("mongo_uri") or "mongodb://localhost:27017"
            mongo_database = self._metadata.get("mongo_database")
            if not mongo_database:
                raise ValueError(
                    "Run metadata has storage_type 'mongo' but no mongo_database; "
                    "metadata may be from an older run or corrupted."
                )
            MongoSharedData = _get_mongo_shared_data_class()
            from pymongo import MongoClient
            client = MongoClient(mongo_uri)
            self._adapter = MongoSharedData(client[mongo_database])
            return self._adapter
        if storage == "memory":
            raise ValueError(
                "Posterior analysis by run_id is not supported for in-memory runs; "
                "data is ephemeral. Use session.inspect() during the run."
            )
        raise NotImplementedError(
            f"Analysis resolution for storage_type={storage!r} is not implemented"
        )

    def inspect(self, kind: str) -> List[SimpleRecord]:
        """Return records of the given kind (e.g. 'outcome', 'trace', 'agent_update')."""
        adapter = self._get_adapter()
        return list(adapter.listen(kind))


def resolve_run(
    run_id: str,
    output_base: str | Path = "./output",
) -> _ResolvedRun:
    """Resolve run_id to a read-only run view with inspect(kind).

    Reads metadata from output_base/run_id/metadata.json. For file-backed runs,
    opens the records directory; for mongo-backed runs, connects using
    metadata mongo_uri and mongo_database. Returns an object that supports
    inspect(kind) like Session.

    Raises:
        FileNotFoundError: If metadata or records path is missing.
        ValueError: If storage_type is 'memory' (no posterior analysis) or mongo metadata is incomplete.
        ImportError: If storage_type is 'mongo' and pymongo is not installed.
        NotImplementedError: If storage_type is not supported.
    """
    metadata = _load_metadata(run_id, output_base)
    return _ResolvedRun(run_id, metadata, Path(output_base))
