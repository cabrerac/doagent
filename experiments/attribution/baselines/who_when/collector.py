"""Who&When-style collector: persist agent utterances only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from experiments.attribution.baselines.protocol import step_output


class OutputLogCollector:
    """Record ordered agent outputs. Step inputs are discarded."""

    name = "w"
    filename = "who_when.json"

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
        """Keep the utterance of one scored decision."""
        del request
        self._steps.append(
            {
                "step": step,
                "agent": agent,
                "content": step_output(response),
            }
        )

    def steps(self) -> List[Dict[str, Any]]:
        """Return output-only steps in order."""
        return list(self._steps)

    def write(self, path: str | Path) -> str:
        """Write the Who&When pack as JSON."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.steps(), indent=2) + "\n", encoding="utf-8")
        return str(target)
