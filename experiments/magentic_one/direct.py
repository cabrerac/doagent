"""Run the stand-in team by passing each result to the next policy.

Optional collectors are notified after each decision.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable

from experiments.attribution.baselines.protocol import StepCollector, notify
from experiments.magentic_one.query import (
    FILE_CODE,
    FILE_SURFER,
    FROZEN_QUERY,
    ORCHESTRATOR,
    WEB_CODE,
    WEB_SURFER,
    gold_record,
)
from experiments.magentic_one.team import (
    file_surfer_policy_factory,
    orchestrator_policy_factory,
    web_surfer_policy_factory,
)


def run_direct_team(
    query: Dict[str, Any] | None = None,
    plant: Dict[str, Any] | None = None,
    collectors: Iterable[StepCollector] = (),
) -> Dict[str, Any]:
    """Run assign, web report, file report, and accept, passing each result along.

    Args:
        query:
            Query id and text.
            The frozen crate query is used when this is omitted.
        plant:
            Optional wrong_fact and ledger_fact.
            The mode must be accept_last.
        collectors:
            Observers notified after each decision.
            No observers are attached when this is omitted.

    Returns:
        Gold labels, the assignment, both reported codes, the responses, and any collector packs.

    Raises:
        ValueError:
            If the plant mode is outside accept_last.
    """
    task = dict(query or FROZEN_QUERY)
    spec = dict(plant or {})
    spec.setdefault("mode", "accept_last")
    spec.setdefault("wrong_fact", WEB_CODE)
    spec.setdefault("ledger_fact", FILE_CODE)
    if spec["mode"] != "accept_last":
        raise ValueError("This run supports accept_last.")

    watchers = tuple(collectors)
    orchestrator = orchestrator_policy_factory({"query": task})
    surfer = web_surfer_policy_factory({"wrong_fact": spec["wrong_fact"]})
    reader = file_surfer_policy_factory({"ledger_fact": spec["ledger_fact"]})

    assign_request = {"goal": "answer-the-query", "inputs": {"query": task}}
    assign_response = orchestrator(assign_request)
    notify(
        watchers,
        step=0,
        agent=ORCHESTRATOR,
        request=assign_request,
        response=assign_response,
    )
    assignment = (assign_response.get("choice") or {}).get("action") or {}

    web_request = {
        "goal": "answer-the-query",
        "inputs": {"assignment": assignment},
    }
    web_response = surfer(web_request)
    notify(
        watchers,
        step=1,
        agent=WEB_SURFER,
        request=web_request,
        response=web_response,
    )
    web_result = (web_response.get("choice") or {}).get("action") or {}

    file_assign_request = {
        "goal": "answer-the-query",
        "inputs": {"query": task, "web_result": web_result},
    }
    file_assign_response = orchestrator(file_assign_request)
    notify(
        watchers,
        step=2,
        agent=ORCHESTRATOR,
        request=file_assign_request,
        response=file_assign_response,
    )
    file_assignment = (file_assign_response.get("choice") or {}).get("action") or {}

    file_request = {
        "goal": "answer-the-query",
        "inputs": {"assignment": file_assignment},
    }
    file_response = reader(file_request)
    notify(
        watchers,
        step=3,
        agent=FILE_SURFER,
        request=file_request,
        response=file_response,
    )
    file_result = (file_response.get("choice") or {}).get("action") or {}

    accept_request = {
        "goal": "answer-the-query",
        "inputs": {
            "query": task,
            "web_result": web_result,
            "file_result": file_result,
        },
    }
    accept_response = orchestrator(accept_request)
    notify(
        watchers,
        step=4,
        agent=ORCHESTRATOR,
        request=accept_request,
        response=accept_response,
    )

    return {
        "gold": gold_record(task, spec),
        "assignment": assignment,
        "web_result": web_result,
        "file_result": file_result,
        "responses": [
            assign_response,
            web_response,
            file_assign_response,
            file_response,
            accept_response,
        ],
        "packs": {item.name: item.steps() for item in watchers},
    }
