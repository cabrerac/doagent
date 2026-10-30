"""Select which MARBLE logs an analyst may open."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

COMPONENT_LOGS = (
    "HiddenProfileEngine.log",
    "HiddenProfileEnv.log",
    "HiddenProfileAgent.agent-a.log",
    "HiddenProfileAgent.agent-b.log",
    "HiddenProfileAgent.agent-c.log",
)


def analyst_logs(
    log_dir: str | Path,
    condition: str,
    names: str | Sequence[str] | None = None,
) -> tuple[Path, ...]:
    """Return the log files one analyst view may open.

    The run has already written every component log.
    S1 opens one named log.
    Sk opens the named subset, in the order given.
    Sall opens every component log.

    Args:
        log_dir: Directory that contains the component log files.
        condition: Analyst view, one of S1, Sk, or Sall.
        names: File names for S1 or Sk.
            S1 takes one name.
            Sk takes one or more names.
            Sall takes no names.

    Returns:
        Paths of the logs in the view.

    Raises:
        ValueError: The view, the name list, or a named file is not valid.
    """
    folder = Path(log_dir)
    selected = component_names(condition, names)
    missing = [name for name in selected if not (folder / name).is_file()]
    if missing:
        raise ValueError(f"missing log files: {', '.join(missing)}")
    return tuple(folder / name for name in selected)


def component_names(
    condition: str,
    names: str | Sequence[str] | None = None,
) -> tuple[str, ...]:
    """Return the component log file names one view writes.

    S1 returns one named log.
    Sk returns the named logs, in the order given.
    Sall returns every component log.

    Args:
        condition: Analyst view, one of S1, Sk, or Sall.
        names: File names for S1 or Sk.
            S1 takes one name.
            Sk takes one or more names.
            Sall takes no names.

    Returns:
        Log file names for that view.

    Raises:
        ValueError: The view or the name list is not valid.
    """
    requested = _names(names)
    if condition == "Sall":
        if requested:
            raise ValueError("Sall takes no names")
        return COMPONENT_LOGS
    if condition == "S1":
        if len(requested) != 1:
            raise ValueError("S1 takes one log name")
    elif condition == "Sk":
        if not requested:
            raise ValueError("Sk takes one or more log names")
    else:
        raise ValueError("condition must be S1, Sk, or Sall")
    unknown = [name for name in requested if name not in COMPONENT_LOGS]
    if unknown:
        raise ValueError(f"unknown log files: {', '.join(unknown)}")
    if len(requested) != len(set(requested)):
        raise ValueError("log names must be unique")
    return requested


def _names(names: str | Sequence[str] | None) -> tuple[str, ...]:
    """Return the caller's log names as a tuple."""
    if names is None:
        return ()
    if isinstance(names, str):
        return (names,)
    return tuple(names)
