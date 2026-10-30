"""Count files, bytes, and joins for one Hidden Profile artifact view."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReadingCost:
    """Cost of reading one artifact view.

    Args:
        files_opened: Files whose contents are read.
        bytes_read: Combined size of those files.
        joins: Cross-file combinations used to build the event list.
    """

    files_opened: int
    bytes_read: int
    joins: int


def session_reading(records_path: str | Path) -> ReadingCost:
    """Count the cost of reading one session export.

    Args:
        records_path: Path of the records file.

    Returns:
        One file, its size, and no joins.

    Raises:
        ValueError: The records file is missing.
    """
    path = Path(records_path)
    if not path.is_file():
        raise ValueError("the session file is missing")
    return ReadingCost(files_opened=1, bytes_read=path.stat().st_size, joins=0)


def log_reading(logs: Sequence[str | Path]) -> ReadingCost:
    """Count the cost of reading the MARBLE logs a parser would open.

    The engine log is ignored.
    Two or more agent logs count as one join.
    An environment log read with an agent log counts as one more join.

    Args:
        logs: Log files the analyst view selected.

    Returns:
        Files read, their combined size, and the join count.

    Raises:
        ValueError: A log the parser would read is missing.
    """
    selected = [Path(path) for path in logs]
    env_logs = [path for path in selected if path.name == "HiddenProfileEnv.log"]
    agent_logs = [
        path
        for path in selected
        if path.name.startswith("HiddenProfileAgent.") and path.suffix == ".log"
    ]
    read = [*env_logs[:1], *agent_logs]
    missing = [path.name for path in read if not path.is_file()]
    if missing:
        raise ValueError(f"missing log files: {', '.join(missing)}")
    joins = 0
    if len(agent_logs) >= 2:
        joins += 1
    if env_logs and agent_logs:
        joins += 1
    return ReadingCost(
        files_opened=len(read),
        bytes_read=sum(path.stat().st_size for path in read),
        joins=joins,
    )
