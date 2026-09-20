"""Policies used by the push example and its experiments."""

from __future__ import annotations

import random
from typing import Any, Dict

from examples._shared.llm_policy import llm_decide_factory


def _action_from_vector(dx: float, dy: float) -> int:
    if abs(dx) < 1e-6 and abs(dy) < 1e-3:
        return 0
    if abs(dx) >= abs(dy):
        return 2 if dx > 0 else 1
    return 4 if dy > 0 else 3


def _epsilon_greedy(base: int, epsilon: float, rng: random.Random) -> int:
    return rng.choice([0, 1, 2, 3, 4]) if rng.random() < epsilon else base


def heuristic_goal_seek(params: Dict[str, Any]) -> Any:
    epsilon = float(params.get("epsilon", 0.0))
    rng = random.Random(params.get("seed", 0))

    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        obs = request.get("inputs", {}).get("observation", [])
        dx, dy = (float(obs[2]), float(obs[3])) if len(obs) >= 4 else (0.0, 0.0)
        return {"choice": {"status": "act", "action": _epsilon_greedy(_action_from_vector(dx, dy), epsilon, rng)}}

    return decide


def heuristic_push_block(params: Dict[str, Any]) -> Any:
    epsilon = float(params.get("epsilon", 0.0))
    rng = random.Random(params.get("seed", 0))

    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        obs = request.get("inputs", {}).get("observation", [])
        dx, dy = (float(obs[6]), float(obs[7])) if len(obs) >= 8 else (0.0, 0.0)
        return {"choice": {"status": "act", "action": _epsilon_greedy(_action_from_vector(dx, dy), epsilon, rng)}}

    return decide


def fixed_policy(params: Dict[str, Any]) -> Any:
    """Return a policy that always chooses the configured integer action."""
    action = int(params.get("action", 0))

    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        return {"choice": {"status": "act", "action": action}}

    return decide


def push_llm_policy_factory(params: Dict[str, Any]) -> Any:
    """LLM policy factory specialised for the push environment."""
    merged = {
        "action_space": {0: "noop", 1: "left", 2: "right", 3: "down", 4: "up"},
        "confidence_threshold": 0.3,
        **params,
    }
    return llm_decide_factory(merged)


def make_agent_configs() -> list[Dict[str, Any]]:
    """Agent configs as plain dicts: id, policy, metadata."""
    return [
        {
            "id": "adversary_0",
            "policy": {"name": "heuristic_push_block", "params": {"epsilon": 0.2, "seed": 1}},
            "metadata": {"explanation": "Heuristic push/block with epsilon-greedy exploration."},
        },
        {
            "id": "agent_0",
            "policy": {"name": "heuristic_goal_seek", "params": {"epsilon": 0.2, "seed": 2}},
            "metadata": {"explanation": "Heuristic goal-seek with epsilon-greedy exploration."},
        },
    ]
