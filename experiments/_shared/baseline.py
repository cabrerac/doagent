"""Baseline comparison helpers for experiment runs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from time import perf_counter
from typing import Callable, Dict

# NoOpSharedData lives in doagent.core.noop_adapter for Session.from_config;
# experiment scripts can import it from doagent.core if needed.


@dataclass(frozen=True)
class BaselineMetrics:
    """Summary metrics for baseline comparison runs."""

    elapsed_seconds: float
    output_bytes: int


def output_bytes_from_path(path: str | Path | None) -> int:
    """Return the size of a file, or of every file under a directory.

    Run folders store records and analysis in subfolders, so a top-level
    listing would under-count recording cost.
    """
    if path is None:
        return 0
    p = Path(path)
    if not p.exists():
        return 0
    if p.is_file():
        return p.stat().st_size
    return sum(
        child.stat().st_size for child in p.rglob("*") if child.is_file()
    )


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
