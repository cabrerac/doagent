"""Minimal environment for the addition-team example.

There is no grid or simulator.
Each agent observes the same query ``{"a": ..., "b": ...}``.
``step`` records the latest actions and returns that same query so the Session API has a normal environment to wrap.
"""

from __future__ import annotations

from typing import Any, Dict, List


class ArithmeticEnv:
    """Shared query for orchestrator, solver, and checker.

    Parameters
    ----------
    query:
        Mapping with integer fields ``a`` and ``b`` (the numbers to add).
    """

    def __init__(self, query: Dict[str, Any]) -> None:
        self.query = dict(query)
        self.agents: List[str] = ["orchestrator", "solver", "checker"]

    def reset(self, *, seed: int | None = None) -> Dict[str, Dict[str, Any]]:
        """Return the query as each agent's first observation."""
        obs = {"query": dict(self.query)}
        return {aid: dict(obs) for aid in self.agents}

    def step(self, actions: Dict[str, Any]) -> Dict[str, Any]:
        """Echo the query and the actions just taken. Rewards stay zero."""
        obs = {
            aid: {"query": dict(self.query), "last_actions": dict(actions)}
            for aid in self.agents
        }
        rewards = {aid: 0.0 for aid in self.agents}
        done = {aid: False for aid in self.agents}
        return {"observations": obs, "rewards": rewards, "done": done}
