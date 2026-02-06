"""Run reporting helpers for validation scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RunReporter:
    """Collect and print runtime/final summaries for validation runs."""

    label: str
    print_every: int = 0
    total_rewards: Dict[str, float] = field(default_factory=dict)
    last_actions: Optional[Dict[str, Any]] = None
    last_rewards: Optional[Dict[str, float]] = None

    def on_outcome(
        self,
        round_id: int,
        actions: Dict[str, Any],
        rewards: Dict[str, float],
    ) -> None:
        for agent, reward in rewards.items():
            self.total_rewards[agent] = self.total_rewards.get(agent, 0.0) + reward
        self.last_actions = dict(actions)
        self.last_rewards = dict(rewards)
        if self.print_every > 0 and round_id % self.print_every == 0:
            print(
                f"[{self.label}] round={round_id} "
                f"actions={actions} rewards={rewards}"
            )

    def finalize(
        self,
        *,
        rounds: int,
        seed: int,
        outcomes: int,
        elapsed_seconds: float,
        output_bytes: int,
        render: bool,
        path: Optional[str] = None,
    ) -> None:
        avg_rewards = {
            agent: (total / outcomes if outcomes else 0.0)
            for agent, total in self.total_rewards.items()
        }
        summary = (
            f"[{self.label}] rounds={rounds} seed={seed} outcomes={outcomes} "
            f"elapsed={elapsed_seconds:.4f}s output_bytes={output_bytes} "
            f"render={'on' if render else 'off'}"
        )
        if path:
            summary += f" path={path}"
        print(summary)
        print(f"  total_rewards={self.total_rewards} avg_rewards={avg_rewards}")
        if self.last_actions is not None and self.last_rewards is not None:
            print(
                f"  last_outcome actions={self.last_actions} "
                f"rewards={self.last_rewards}"
            )
