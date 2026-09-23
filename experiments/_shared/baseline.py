"""Baseline comparison helpers for experiment runs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from time import perf_counter
from typing import Callable, Dict


@dataclass(frozen=True)
class BaselineMetrics:
    """Hold elapsed time and output size for one baseline run."""

    elapsed_seconds: float
    output_bytes: int


def output_bytes_from_path(path: str | Path | None) -> int:
    """Return the size of a file, or of every file under a directory.

    Args:
        path:
            File or directory to measure.
            Zero is returned when the path is missing.

    Returns:
        Size in bytes.
        A directory total includes every file in subfolders.
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
    """Time one run and count the bytes it leaves.

    Args:
        run_fn:
            Callable that performs the run.
        output_path:
            File or directory whose size is counted after the run.

    Returns:
        Elapsed seconds and output bytes.
    """
    start = perf_counter()
    run_fn()
    elapsed = perf_counter() - start
    return BaselineMetrics(
        elapsed_seconds=elapsed,
        output_bytes=output_bytes_from_path(output_path),
    )


def write_summary(path: str | Path, payload: Dict[str, object]) -> None:
    """Write a JSON summary.

    Args:
        path:
            File to write.
        payload:
            Mapping to store.
    """
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
