"""TraceElephant-static collector: persist step input and output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from experiments.attribution.baselines.protocol import step_input, step_output


class StepIOCollector:
    """Record each scored step's task-facing input and output."""

    name = "t"
    filename = "trace_elephant.json"

    def __init__(self) -> None:
        self._steps: List[Dict[str, Any]] = []

    def on_step(
        self,
        *,
        step: int,
        agent: str,
        request: Dict[str, Any],
        response: Dict[str, Any],
    ) -> None:
        """Keep the intercepted input and output of one scored decision."""
        self._steps.append(
            {
                "step": step,
                "agent": agent,
                "input": step_input(request),
                "output": step_output(response),
            }
        )

    def steps(self) -> List[Dict[str, Any]]:
        """Return input-and-output steps in order."""
        return list(self._steps)

    def write(self, path: str | Path) -> str:
        """Write the TraceElephant-static pack as JSON."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.steps(), indent=2) + "\n", encoding="utf-8")
        return str(target)
