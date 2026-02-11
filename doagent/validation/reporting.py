"""Run reporting helpers for validation scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional


@dataclass
class RunReporter:
    """Collect and print runtime/final summaries for validation runs."""

    label: str
    print_every: int = 0
    record_series: bool = True
    series_every: int = 1
    record_entropy: bool = True
    action_space: int = 5
    total_rewards: Dict[str, float] = field(default_factory=dict)
    min_rewards: Dict[str, float] = field(default_factory=dict)
    max_rewards: Dict[str, float] = field(default_factory=dict)
    reward_series: List[Dict[str, float]] = field(default_factory=list)
    action_counts: Dict[str, Dict[str, int]] = field(default_factory=dict)
    last_actions: Optional[Dict[str, Any]] = None
    last_rewards: Optional[Dict[str, float]] = None
    extra_metrics: Dict[str, object] = field(default_factory=dict)

    def on_outcome(
        self,
        round_id: int,
        actions: Dict[str, Any],
        rewards: Dict[str, float],
    ) -> None:
        for agent, reward in rewards.items():
            self.total_rewards[agent] = self.total_rewards.get(agent, 0.0) + reward
            if agent not in self.min_rewards:
                self.min_rewards[agent] = reward
                self.max_rewards[agent] = reward
            else:
                self.min_rewards[agent] = min(self.min_rewards[agent], reward)
                self.max_rewards[agent] = max(self.max_rewards[agent], reward)
        for agent, action in actions.items():
            agent_counts = self.action_counts.setdefault(agent, {})
            key = str(action)
            agent_counts[key] = agent_counts.get(key, 0) + 1
        self.last_actions = dict(actions)
        self.last_rewards = dict(rewards)
        if self.record_series and round_id % max(self.series_every, 1) == 0:
            self.reward_series.append(dict(rewards))
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

    def _entropy(self, counts: Dict[str, int]) -> tuple[float, float]:
        total = sum(counts.values())
        if total <= 0:
            return 0.0, 0.0
        entropy = 0.0
        for value in counts.values():
            if value <= 0:
                continue
            p = value / total
            entropy -= p * math.log2(p)
        max_entropy = math.log2(self.action_space) if self.action_space > 1 else 1.0
        normalized = entropy / max_entropy if max_entropy > 0 else 0.0
        return entropy, normalized

    def metrics(
        self,
        *,
        outcomes: int,
        extra: Optional[Dict[str, object]] = None,
    ) -> Dict[str, object]:
        avg_rewards = {
            agent: (total / outcomes if outcomes else 0.0)
            for agent, total in self.total_rewards.items()
        }
        entropies: Dict[str, object] = {}
        if self.record_entropy:
            for agent, counts in self.action_counts.items():
                raw, normalized = self._entropy(counts)
                entropies[agent] = {
                    "raw": raw,
                    "normalized": normalized,
                }
        payload: Dict[str, object] = {
            "total_rewards": dict(self.total_rewards),
            "avg_rewards": avg_rewards,
            "min_rewards": dict(self.min_rewards),
            "max_rewards": dict(self.max_rewards),
            "action_counts": self.action_counts,
        }
        if entropies:
            payload["action_entropy"] = entropies
        if self.record_series:
            payload["reward_series"] = self.reward_series
            payload["series_every"] = self.series_every
        if self.last_actions is not None and self.last_rewards is not None:
            payload["last_outcome"] = {
                "actions": self.last_actions,
                "rewards": self.last_rewards,
            }
        merged_extra = dict(self.extra_metrics)
        if extra:
            merged_extra.update(extra)
        if merged_extra:
            payload["extra_metrics"] = merged_extra
        return payload
