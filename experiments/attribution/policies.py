"""Build scripted policies for the addition team.

Each factory returns a decide callable.
A planted value can replace the honest sum or the honest accept decision.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _assignment_from_choice(action: Any) -> Optional[Dict[str, Any]]:
    """Return the assignment fields when the action assigns a task.

    Args:
        action:
            Choice action from a decision.

    Returns:
        A mapping with assignee, op, a, and b.
        None for any other action.

    Raises:
        KeyError:
            If the action assigns a task but omits a or b.
    """
    if isinstance(action, dict) and action.get("type") == "assign":
        return {
            "assignee": action.get("assignee", "solver"),
            "op": action.get("op", "add"),
            "a": action["a"],
            "b": action["b"],
        }
    return None


def latest_assignment(records: List[Any]) -> Optional[Dict[str, Any]]:
    """Return the latest assignment found in the given records.

    The search checks each decision action first.
    It then checks an assignment stored on the record.

    Args:
        records:
            Records to search, newest last.

    Returns:
        The assignment mapping.
        None when no assignment is present.
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
    """Return the latest solver value found in the given records.

    The search checks a stored solver value first.
    It then checks a solve action on a decision.

    Args:
        records:
            Records to search, newest last.

    Returns:
        The reported value.
        None when no solver value is present.
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
    """Build a policy that assigns the solver to add two numbers.

    Args:
        params:
            Optional query with keys a and b.

    Returns:
        A decide callable.
    """

    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        """Assign the solver to add the two query numbers.

        Args:
            request:
                Decision request.
                The query is read from inputs, then from the factory params.

        Returns:
            A choice that assigns the solver, plus a short explanation.
        """
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
    """Build a policy that reports a sum for the assigned pair.

    Args:
        params:
            Optional plant_wrong_sum.
            When set, that value is reported instead of the true sum.

    Returns:
        A decide callable.
    """
    planted = params.get("plant_wrong_sum")

    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        """Report a sum for the assigned pair.

        Args:
            request:
                Decision request with the assignment in inputs.

        Returns:
            A choice whose action holds the reported value, plus a short explanation.
        """
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
    """Build a policy that accepts or rejects the reported sum.

    Args:
        params:
            Optional plant_accept_wrong, true by default.
            A true value accepts every report.
            A false value accepts only when the report equals the true sum.

    Returns:
        A decide callable.
    """
    plant_accept_wrong = bool(params.get("plant_accept_wrong", True))

    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        """Accept or reject the reported sum.

        Args:
            request:
                Decision request with the assignment and the solver value.

        Returns:
            A choice that records the accept decision, plus a short explanation.
        """
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
