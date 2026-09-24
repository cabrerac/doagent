"""Read and write a truth file of facts, holders, and votes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def write_truth(path: Path, document: Mapping[str, Any]) -> None:
    """Write the truth document as JSON.

    Args:
        path: Destination file.
        document: Phases, facts, holders, and votes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")


def read_truth(path: Path) -> dict[str, Any]:
    """Read a truth document from JSON.

    Args:
        path: Truth file written during a run.

    Returns:
        The document as a dictionary.
    """
    return json.loads(path.read_text(encoding="utf-8"))
