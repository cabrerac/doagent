"""No-op shared data adapter for baseline / no-recording runs."""

from __future__ import annotations

from typing import Iterable, Optional

from ...interface.shared_data import SharedDataAdapter
from ...records import SimpleRecord


class NoOpSharedData(SharedDataAdapter):
    """Shared data adapter that discards writes for baseline runs."""

    def write(self, record: SimpleRecord) -> None:
        return None

    def read(self, record_id: str) -> Optional[SimpleRecord]:
        return None

    def list(self) -> Iterable[SimpleRecord]:
        return []

    def listen(
        self,
        kind: str,
        *,
        actor: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> Iterable[SimpleRecord]:
        return []
