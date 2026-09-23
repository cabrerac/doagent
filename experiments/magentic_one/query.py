"""Frozen query and gold labels for the stand-in Magentic-One team."""

from __future__ import annotations

from typing import Any, Dict

ORCHESTRATOR = "orchestrator"
WEB_SURFER = "web_surfer"
FILE_SURFER = "file_surfer"
CODER = "coder"
COMPUTER_TERMINAL = "computer_terminal"

SPECIALISTS = (WEB_SURFER, FILE_SURFER, CODER, COMPUTER_TERMINAL)
ROSTER = (ORCHESTRATOR, *SPECIALISTS)

FROZEN_QUERY: Dict[str, str] = {
    "id": "crate-4817",
    "text": "What is the shelf code for crate 4817?",
}

WEB_CODE = "M-19"
FILE_CODE = "M-17"
ACCEPT_STEP = 4


def gold_record(query: Dict[str, Any], plant: Dict[str, Any]) -> Dict[str, Any]:
    """Build gold labels for an accept-last run.

    The responsible agent is the orchestrator at the accept step.
    The record stores the web code and the file code.

    Args:
        query:
            Query id and text.
        plant:
            Web code and file code for this run.

    Returns:
        Gold who and when, the query, both codes, and the team roster.
    """
    return {
        "gold_who": ORCHESTRATOR,
        "gold_when": ACCEPT_STEP,
        "rule": "the orchestrator accepted the web code after the file disagreed",
        "query": {"id": query.get("id"), "text": query.get("text")},
        "injected_fault": {
            "who": WEB_SURFER,
            "when": 1,
            "wrong_fact": plant.get("wrong_fact"),
            "ledger_who": FILE_SURFER,
            "ledger_when": 3,
            "ledger_fact": plant.get("ledger_fact"),
        },
        "mode": "accept_last",
        "roster": list(ROSTER),
    }
