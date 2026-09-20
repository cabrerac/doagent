"""Addition team without DOAgent: the host loop passes return values.

This is the cost-run host for W-only and T-only.
Collectors watch the run, but are not the mailbox.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable

from experiments.attribution.baselines.protocol import StepCollector, notify
from experiments.attribution.labels import (
    CHECKER,
    ORCHESTRATOR,
    SOLVER,
    gold_record,
)
from experiments.attribution.policies import (
    checker_policy_factory,
    orchestrator_policy_factory,
    solver_policy_factory,
)


def run_direct_team(
    query: Dict[str, Any],
    plant: Dict[str, Any],
    collectors: Iterable[StepCollector] = (),
) -> Dict[str, Any]:
    """Run assign, solve, then check with in-process hand-off."""
    watchers = tuple(collectors)
    orch = orchestrator_policy_factory({"query": query})
    solver = solver_policy_factory(
        {"plant_wrong_sum": plant.get("plant_wrong_sum")}
    )
    checker = checker_policy_factory(
        {"plant_accept_wrong": plant.get("plant_accept_wrong", True)}
    )

    assign_request = {
        "goal": "add-two-numbers",
        "inputs": {"query": query},
    }
    assign_response = orch(assign_request)
    notify(
        watchers,
        step=0,
        agent=ORCHESTRATOR,
        request=assign_request,
        response=assign_response,
    )
    action = (assign_response.get("choice") or {}).get("action") or {}
    assignment = {
        "assignee": action.get("assignee", SOLVER),
        "op": action.get("op", "add"),
        "a": action["a"],
        "b": action["b"],
    }

    solve_request = {
        "goal": "add-two-numbers",
        "inputs": {"assignment": assignment},
    }
    solve_response = solver(solve_request)
    notify(
        watchers,
        step=1,
        agent=SOLVER,
        request=solve_request,
        response=solve_response,
    )
    solver_value = solve_response["choice"]["action"]["value"]

    check_request = {
        "goal": "add-two-numbers",
        "inputs": {
            "assignment": assignment,
            "solver_value": solver_value,
        },
    }
    check_response = checker(check_request)
    notify(
        watchers,
        step=2,
        agent=CHECKER,
        request=check_request,
        response=check_response,
    )

    return {
        "gold": gold_record(query, plant),
        "assignment": assignment,
        "solver_value": solver_value,
        "responses": [assign_response, solve_response, check_response],
        "packs": {item.name: item.steps() for item in watchers},
    }
