"""Choose disclosures and votes for Hidden Profile."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from .rules import Fact, option_belief


def scripted_policy(
    agent_id: str,
) -> Callable[[Mapping[str, object]], dict[str, object]]:
    """Return the scripted disclosure and vote policy for one agent.

    Args:
        agent_id: Identifier of the agent that will use the policy.

    Returns:
        A function from a decision request to a choice.

    Raises:
        ValueError: The observation phase or the held facts are invalid.
    """
    del agent_id

    def choose(request: Mapping[str, object]) -> dict[str, object]:
        """Disclose the next dealt fact, or vote for the leading option."""
        observation = _observation(request)
        phase = observation.get("phase")
        if phase == "disclose":
            action = _disclose(observation)
        elif phase == "vote":
            action = _vote(observation)
        else:
            raise ValueError("phase must be disclose or vote")
        return {"choice": {"action": action}}

    return choose


def _observation(request: Mapping[str, object]) -> Mapping[str, object]:
    """Read the observation from a request or from a bare mapping."""
    inputs = request.get("inputs")
    if isinstance(inputs, Mapping) and "observation" in inputs:
        observation = inputs["observation"]
    else:
        observation = request
    if not isinstance(observation, Mapping):
        raise ValueError("observation must be a mapping")
    return observation


def _disclose(observation: Mapping[str, object]) -> dict[str, object]:
    """Return the next dealt fact in identifier order."""
    held = _items(observation.get("held_facts"))
    recipients = _items(observation.get("recipients"))
    round_index = observation.get("round")
    if (
        held is None
        or recipients is None
        or isinstance(round_index, bool)
        or not isinstance(round_index, int)
    ):
        raise ValueError("a disclosure observation is incomplete")
    dealt = tuple(
        fact
        for fact in held
        if isinstance(fact, Mapping) and fact.get("origin") == "dealt"
    )
    ordered = tuple(sorted(dealt, key=lambda fact: str(fact["fact_id"])))
    if round_index >= len(ordered):
        return {"kind": "disclose", "fact_id": None, "recipients": ()}
    return {
        "kind": "disclose",
        "fact_id": ordered[round_index]["fact_id"],
        "recipients": recipients,
    }


def _vote(observation: Mapping[str, object]) -> dict[str, object]:
    """Return the first option with the highest declared score."""
    held = _items(observation.get("held_facts"))
    options = _items(observation.get("options"))
    if held is None or options is None:
        raise ValueError("a vote observation is incomplete")
    facts = tuple(
        Fact(
            str(fact["fact_id"]),
            str(fact["option"]),
            int(fact["weight"]),
            fact.get("origin") == "shared",
        )
        for fact in held
        if isinstance(fact, Mapping)
    )
    probabilities = option_belief(facts, options)
    best = max(probabilities)
    for option, probability in zip(options, probabilities):
        if probability == best:
            return {"kind": "vote", "option": option}
    return {"kind": "vote", "option": options[0]}


def _items(value: object) -> tuple[object, ...] | None:
    """Return a sequence as a tuple.

    Args:
        value: Candidate sequence.

    Returns:
        The values, or None when value is not a sequence.
    """
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(value)
    return None
