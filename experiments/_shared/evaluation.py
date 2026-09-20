"""Common result shape for one-condition experiment evaluations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class EvaluationResult:
    """Metrics produced by exactly one measured scenario execution."""

    condition: Dict[str, Any]
    task_metrics: Dict[str, Any]
    elapsed_seconds: float
    output_bytes: int
    run_id: Optional[str]
    run_path: Optional[str]
