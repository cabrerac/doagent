"""Choose messages, beliefs, and actions for the signalling game."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import math

from .environment import EnvironmentConfig


def signalling_policy(
    agent_id: str,
    config: EnvironmentConfig,
) -> Callable[[Mapping[str, object]], dict[str, object]]:
    """Return the scripted policy for one signalling agent.

    Args:
        agent_id: Identifier of the agent that will use the policy.
        config: State alphabet and observation channels the policy knows.

    Returns:
        A function from one observation mapping to one action mapping.

    Raises:
        ValueError: The agent is not configured.
    """
    channels = {
        channel.agent_id: channel
        for channel in config.observation_channels
    }
    if agent_id not in channels:
        raise ValueError("agent_id must identify a configured agent")

    def choose(observation: Mapping[str, object]) -> dict[str, object]:
        """Send the glimpse, or report a belief and a colour."""
        phase = observation.get("phase")
        glimpse = observation.get("observation")
        if not isinstance(glimpse, str) or not glimpse:
            raise ValueError("observation must be a non-empty string")
        if phase == "send":
            if agent_id != config.sender_id:
                raise ValueError("only the sender acts in the send phase")
            return {"kind": "send", "message": glimpse}
        if phase != "decide":
            raise ValueError("phase must be send or decide")
        evidence = [(glimpse, channels[agent_id].accuracy)]
        message = observation.get("message")
        if message is not None:
            if not isinstance(message, str) or not message:
                raise ValueError("message must be a non-empty string")
            evidence.append((message, channels[config.sender_id].accuracy))
        probabilities = _posterior(config.states, evidence)
        action_index = max(
            range(len(config.states)),
            key=probabilities.__getitem__,
        )
        return {
            "kind": "decide",
            "probabilities": probabilities,
            "action": config.states[action_index],
        }

    return choose


def _posterior(
    states: tuple[str, ...],
    evidence: list[tuple[str, float]],
) -> tuple[float, ...]:
    """Return the Bayesian posterior under independent symmetric channels."""
    weights = []
    for candidate in states:
        weight = 1.0
        for observation, accuracy in evidence:
            if observation == candidate:
                weight *= accuracy
            else:
                weight *= (1.0 - accuracy) / (len(states) - 1)
        weights.append(weight)
    total = math.fsum(weights)
    if total == 0.0:
        raise ValueError("evidence has zero probability under every hidden state")
    return tuple(weight / total for weight in weights)
