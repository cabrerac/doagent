"""Multiprocessing interface for parallel experiment runs."""

from __future__ import annotations

from dataclasses import asdict
from multiprocessing import Lock, Manager
from typing import Callable, Iterable, Optional

from doagent.interface.shared_data import SharedDataAdapter
from doagent.records import SimpleRecord


class MultiProcessInterface:
    """Interface between processes and a persisted shared-data adapter."""

    def __init__(self, adapter_factory: Callable[[], SharedDataAdapter]) -> None:
        self._adapter_factory = adapter_factory
        manager = Manager()
        self._records = manager.list()
        self._lock = Lock()

    def write_record(self, record: SimpleRecord) -> None:
        payload = asdict(record)
        with self._lock:
            self._records.append(payload)
        adapter = self._adapter_factory()
        adapter.write(record)

    def read_record(self, record_id: str) -> Optional[SimpleRecord]:
        for payload in self._records:
            if payload.get("id") == record_id:
                return SimpleRecord(**payload)
        adapter = self._adapter_factory()
        return adapter.read(record_id)

    def list_records(self) -> Iterable[SimpleRecord]:
        if self._records:
            return [SimpleRecord(**payload) for payload in list(self._records)]
        adapter = self._adapter_factory()
        return list(adapter.list())

    def listen_records(
        self,
        kind: str,
        *,
        actor: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> Iterable[SimpleRecord]:
        records = []
        for payload in list(self._records):
            if payload.get("kind") != kind:
                continue
            if actor is not None and payload.get("actor") != actor:
                continue
            timestamp = payload.get("timestamp")
            if since is not None and timestamp is not None and timestamp < since:
                continue
            if until is not None and timestamp is not None and timestamp > until:
                continue
            records.append(SimpleRecord(**payload))
        if records:
            return records
        adapter = self._adapter_factory()
        return adapter.listen(kind, actor=actor, since=since, until=until)
