"""Record step inputs and outputs for a TraceElephant-style pack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from experiments.attribution.baselines.protocol import step_input, step_output


class StepIOCollector:
    """Record each step's input and output.

    Each stored step has a step index, an agent, an input, and an output.
    """

    name = "t"
    filename = "trace_elephant.json"

    def __init__(self) -> None:
        """Start with an empty step list."""
        self._steps: List[Dict[str, Any]] = []

    def on_step(
        self,
        *,
        step: int,
        agent: str,
        request: Dict[str, Any],
        response: Dict[str, Any],
    ) -> None:
        """Store the input and output of one decision.

        Args:
            step:
                Step index on the shared clock.
            agent:
                Agent that decided.
            request:
                What the policy received.
            response:
                What the policy returned.
        """
        self._steps.append(
            {
                "step": step,
                "agent": agent,
                "input": step_input(request),
                "output": step_output(response),
            }
        )

    def steps(self) -> List[Dict[str, Any]]:
        """Return the stored steps in order.

        Returns:
            One dict per decision, with step, agent, input, and output.
        """
        return list(self._steps)

    def write(self, path: str | Path) -> str:
        """Write the pack as JSON.

        Args:
            path:
                File to write.

        Returns:
            Path of the written file.
        """
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.steps(), indent=2) + "\n", encoding="utf-8")
        return str(target)
