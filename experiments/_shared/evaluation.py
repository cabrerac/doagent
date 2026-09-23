"""Hold the result of one measured experiment run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class EvaluationResult:
    """Hold the metrics from one measured run.

    condition records what was executed.
    task_metrics holds the measured outcomes.
    elapsed_seconds is the wall-clock time.
    output_bytes is the size left on disk.
    run_id and run_path identify the run folder when one was created.
    """

    condition: Dict[str, Any]
    task_metrics: Dict[str, Any]
    elapsed_seconds: float
    output_bytes: int
    run_id: Optional[str]
    run_path: Optional[str]
