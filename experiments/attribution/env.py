"""Hold the addition query for the three agents.

Each agent sees the same query.
step records the latest actions and returns that query again.
"""

from __future__ import annotations

from typing import Any, Dict, List


class ArithmeticEnv:
    """Share one addition query with the orchestrator, solver, and checker."""

    def __init__(self, query: Dict[str, Any]) -> None:
        """Store the query and the three agent names.

        Args:
            query:
                Mapping with integer fields a and b.
        """
        self.query = dict(query)
        self.agents: List[str] = ["orchestrator", "solver", "checker"]

    def reset(self, *, seed: int | None = None) -> Dict[str, Dict[str, Any]]:
        """Return the query as each agent's first observation.

        Args:
            seed:
                Ignored.

        Returns:
            One observation per agent.
            Each observation holds the query.
        """
        obs = {"query": dict(self.query)}
        return {aid: dict(obs) for aid in self.agents}

    def step(self, actions: Dict[str, Any]) -> Dict[str, Any]:
        """Return the query again, together with the actions just taken.

        Args:
            actions:
                Actions submitted on this step.

        Returns:
            Observations, zero rewards, and done false for every agent.
        """
        obs = {
            aid: {"query": dict(self.query), "last_actions": dict(actions)}
            for aid in self.agents
        }
        rewards = {aid: 0.0 for aid in self.agents}
        done = {aid: False for aid in self.agents}
        return {"observations": obs, "rewards": rewards, "done": done}
