"""Gold labels and agent ids for the addition-team experiment."""

from __future__ import annotations

from typing import Any, Dict

ORCHESTRATOR = "orchestrator"
SOLVER = "solver"
CHECKER = "checker"

# Decisive error step when the checker accepts a wrong sum (0-based).
CHECK_STEP_INDEX = 2


def gold_record(query: Dict[str, Any], plant: Dict[str, Any]) -> Dict[str, Any]:
    """Labels for who is responsible and at which step.

    The solver may inject a wrong sum first.
    This example treats the checker as responsible when it accepts that sum: a later agent was expected to catch the error and did not.
    """
    a, b = int(query["a"]), int(query["b"])
    return {
        "gold_who": CHECKER,
        "gold_when": CHECK_STEP_INDEX,
        "rule": "the checker should have rejected the wrong sum",
        "query": {"a": a, "b": b, "correct": a + b},
        "injected_fault": {
            "who": SOLVER,
            "when": 1,
            "plant_wrong_sum": plant.get("plant_wrong_sum"),
        },
        "plant_accept_wrong": plant.get("plant_accept_wrong", True),
    }
