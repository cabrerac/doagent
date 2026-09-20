"""Scripted policies for the addition-team example.

Each factory returns a ``decide(request)`` callable that the Session wraps.
Policies are deterministic so a run can inject a known wrong sum and a
known missed check without calling a language model.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _assignment_from_choice(action: Any) -> Optional[Dict[str, Any]]:
    """Return ``{assignee, op, a, b}`` if *action* is an assign payload."""
    if isinstance(action, dict) and action.get("type") == "assign":
        return {
            "assignee": action.get("assignee", "solver"),
            "op": action.get("op", "add"),
            "a": action["a"],
            "b": action["b"],
        }
    return None


def latest_assignment(records: List[Any]) -> Optional[Dict[str, Any]]:
    """Find the most recent addition assignment in visible ``agent_update`` records.

    Looks at decision actions first, then at ``local_knowledge['assignment']``
    (used when the orchestrator republishes the task for other agents).
    """
    for record in reversed(records):
        decision = record.payload.get("decision") or {}
        response = decision.get("response") or {}
        choice = response.get("choice") or {}
        found = _assignment_from_choice(choice.get("action"))
        if found is not None:
            return found
        local = record.payload.get("local_knowledge") or {}
        if "assignment" in local and isinstance(local["assignment"], dict):
            return dict(local["assignment"])
    return None


def latest_solver_value(records: List[Any]) -> Optional[Any]:
    """Find the most recent solver result in visible records.

    Prefers a hub republish (``local_knowledge['solver_value']``), then a
    solver decision whose action type is ``solve``.
    """
    for record in reversed(records):
        local = record.payload.get("local_knowledge") or {}
        if "solver_value" in local:
            return local["solver_value"]
        decision = record.payload.get("decision") or {}
        response = decision.get("response") or {}
        action = (response.get("choice") or {}).get("action")
        if isinstance(action, dict) and action.get("type") == "solve":
            return action.get("value")
    return None


def orchestrator_policy_factory(params: Dict[str, Any]):
    """Build a policy that assigns the solver to add ``query['a']`` and ``query['b']``.

    The query is taken from ``request['inputs']['query']``, or from ``params``
    if the inputs omit it.
    """

    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        inputs = request.get("inputs") or {}
        query = inputs.get("query") or params.get("query") or {}
        a, b = int(query["a"]), int(query["b"])
        action = {
            "type": "assign",
            "assignee": "solver",
            "op": "add",
            "a": a,
            "b": b,
        }
        return {
            "choice": {"status": "act", "action": action},
            "explanation": f"Assign solver to add {a} and {b}.",
        }

    return decide


def solver_policy_factory(params: Dict[str, Any]):
    """Build a policy that returns a sum for the assigned pair.

    If ``params['plant_wrong_sum']`` is set, that value is returned instead
    of ``a + b``.
    """
    planted = params.get("plant_wrong_sum")

    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        inputs = request.get("inputs") or {}
        assignment = inputs.get("assignment") or {}
        a, b = int(assignment["a"]), int(assignment["b"])
        correct = a + b
        value = int(planted) if planted is not None else correct
        return {
            "choice": {"status": "act", "action": {"type": "solve", "value": value}},
            "explanation": f"Report {value} for {a}+{b} (correct is {correct}).",
        }

    return decide


def checker_policy_factory(params: Dict[str, Any]):
    """Build a policy that accepts or rejects the solver's value.

    The honest rule is ``accept`` only when the reported value equals
    ``a + b``. If ``params['plant_accept_wrong']`` is true (the default for
    this example), the checker always accepts, including a wrong sum.
    """
    plant_accept_wrong = bool(params.get("plant_accept_wrong", True))

    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        inputs = request.get("inputs") or {}
        assignment = inputs.get("assignment") or {}
        reported = int(inputs["solver_value"])
        a, b = int(assignment["a"]), int(assignment["b"])
        correct = a + b
        should_accept = reported == correct
        accept = True if plant_accept_wrong else should_accept
        return {
            "choice": {
                "status": "act",
                "action": {
                    "type": "check",
                    "accept": accept,
                    "reported": reported,
                    "correct": correct,
                },
            },
            "explanation": (
                f"Checker accept={accept} (reported {reported}, correct {correct})."
            ),
        }

    return decide
