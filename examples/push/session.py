"""Reusable push session function, separate from the CLI entry point."""

from __future__ import annotations

from typing import Any, Dict

from doagent import Session, RunReporter


def run_with_session(
    session: Session,
    env: Any,
    configs: list[Dict[str, Any]],
    rounds: int,
    seed: int,
    *,
    render: bool = False,
    reporter: RunReporter | None = None,
) -> int:
    """Run push scenario using the DOAgent Session API. Returns outcome count."""
    wrapped_env = session.wrap_env(env, env_actor="push_env")
    agents = session.create_agents(
        configs, goal="push_towards_landmark",
    )

    observations = wrapped_env.reset(seed=seed)
    if render:
        wrapped_env.render()

    outcome_count = 0
    for round_id in range(1, rounds + 1):
        actions: Dict[str, Any] = {}
        for agent_id, agent in agents.items():
            result = agent.decide(observations.get(agent_id, {}), round_id)
            action = result["action"]
            actions[agent_id] = action if action is not None else 0

        step = wrapped_env.step(actions)
        if reporter is not None:
            reporter.on_outcome(round_id, actions, step["rewards"])
        if render:
            wrapped_env.render()
        observations = step["observations"]
        outcome_count += 1

    return outcome_count
