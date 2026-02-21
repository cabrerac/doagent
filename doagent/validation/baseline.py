"""Baseline comparison helpers for validation runs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from time import perf_counter
from typing import Callable, Dict, Iterable, Optional

from ..interface.shared_data import SharedDataAdapter
from ..records import SimpleRecord


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


@dataclass(frozen=True)
class BaselineMetrics:
    """Summary metrics for baseline comparison runs."""

    elapsed_seconds: float
    output_bytes: int


def output_bytes_from_path(path: str | Path | None) -> int:
    """Return output size for a path (file or directory), or 0 if missing."""
    if path is None:
        return 0
    p = Path(path)
    if not p.exists():
        return 0
    if p.is_dir():
        return sum(f.stat().st_size for f in p.iterdir() if f.is_file())
    return p.stat().st_size


def measure_baseline(
    run_fn: Callable[[], None],
    *,
    output_path: str | Path | None = None,
) -> BaselineMetrics:
    """Measure elapsed time for a baseline run."""
    start = perf_counter()
    run_fn()
    elapsed = perf_counter() - start
    return BaselineMetrics(
        elapsed_seconds=elapsed,
        output_bytes=output_bytes_from_path(output_path),
    )


def write_summary(path: str | Path, payload: Dict[str, object]) -> None:
    """Write summary metrics to a JSON file."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
