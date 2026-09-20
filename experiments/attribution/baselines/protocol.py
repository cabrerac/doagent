"""Shared observer hook for W and T collectors."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Protocol


class StepCollector(Protocol):
    """Record one scored decision. Must not send data back to the team."""

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
        """See one decision. ``request`` is what the policy received."""

    def steps(self) -> list[Dict[str, Any]]:
        """Return collected steps in order."""


def step_input(request: Dict[str, Any]) -> Dict[str, Any]:
    """Return the task-facing step input, without Session observation blobs."""
    inputs = request.get("inputs") if isinstance(request, dict) else None
    if not isinstance(inputs, dict):
        return {}
    return {key: value for key, value in inputs.items() if key != "observation"}


def step_output(response: Dict[str, Any]) -> Any:
    """Return the action or utterance, not the Session decide envelope."""
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
    """Fan a decision out to observe-only collectors."""
    for collector in collectors:
        collector.on_step(
            step=step,
            agent=agent,
            request=request,
            response=response,
        )
