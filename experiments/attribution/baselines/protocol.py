"""Define the observer hook shared by the W and T collectors."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Protocol


class StepCollector(Protocol):
    """Record one scored decision.

    name is the collector label.
    filename is the pack file written later.
    """

    name: str
    filename: str

    def on_step(
        self,
        *,
        step: int,
        agent: str,
        request: Dict[str, Any],
        response: Dict[str, Any],
    ) -> None:
        """Record one decision.

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

    def steps(self) -> list[Dict[str, Any]]:
        """Return the collected steps in order.

        Returns:
            One dict per recorded decision.
        """


def step_input(request: Dict[str, Any]) -> Dict[str, Any]:
    """Return the task fields from a decision request.

    Args:
        request:
            What the policy received.

    Returns:
        The inputs mapping, with the observation field left out.
    """
    inputs = request.get("inputs") if isinstance(request, dict) else None
    if not isinstance(inputs, dict):
        return {}
    return {key: value for key, value in inputs.items() if key != "observation"}


def step_output(response: Dict[str, Any]) -> Any:
    """Return the action the policy chose.

    Args:
        response:
            What the policy returned.

    Returns:
        The action field when one is present.
        The original value when the response is not a mapping.
        The remaining fields when no action is present.
    """
    if not isinstance(response, dict):
        return response
    choice = response.get("choice")
    if isinstance(choice, dict) and "action" in choice:
        return choice["action"]
    if "action" in response:
        return response["action"]
    return {key: value for key, value in response.items() if key != "explanation"}


def notify(
    collectors: Iterable[StepCollector],
    *,
    step: int,
    agent: str,
    request: Dict[str, Any],
    response: Dict[str, Any],
) -> None:
    """Send one decision to each collector.

    Args:
        collectors:
            Observers to notify.
        step:
            Step index on the shared clock.
        agent:
            Agent that decided.
        request:
            What the policy received.
        response:
            What the policy returned.
    """
    for collector in collectors:
        collector.on_step(
            step=step,
            agent=agent,
            request=request,
            response=response,
        )
