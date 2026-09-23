"""Provide agent ids and gold labels for the addition team."""

from __future__ import annotations

from typing import Any, Dict

ORCHESTRATOR = "orchestrator"
SOLVER = "solver"
CHECKER = "checker"

# Step index of the checker decision. Counting starts at 0.
CHECK_STEP_INDEX = 2


def gold_record(query: Dict[str, Any], plant: Dict[str, Any]) -> Dict[str, Any]:
    """Build the gold labels for one addition run.

    The responsible agent is the checker at step 2.
    The record also stores the solver's planted sum.

    Args:
        query:
            Mapping with integer fields a and b.
        plant:
            Optional plant_wrong_sum and plant_accept_wrong.
            plant_accept_wrong defaults to true.

    Returns:
        Gold who and when, the query with the true sum, the planted fault, and the team roster.
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
        "roster": [ORCHESTRATOR, SOLVER, CHECKER],
    }
