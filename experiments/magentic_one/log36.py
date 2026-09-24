"""Query and labels for Who&When hand-crafted log 36.

The dataset names an answer and a mistake in its own chat.
This run keeps that answer as a reference.
It does not copy their step index onto our decisions.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from experiments.magentic_one.query import ORCHESTRATOR, WEB_SURFER

LOG36_QUERY: Dict[str, str] = {
    "id": "c7afe00869f98cf363fd83677ac41757ed5e57f03eacc3d1304feb0a92084bd1",
    "text": (
        "What is the highest rated (according to IMDB) Daniel Craig movie "
        "that is less than 150 minutes and is available on Netflix (US)?"
    ),
}

REFERENCE_ANSWER = "Glass Onion: A Knives Out Mystery"
DATASET_MISTAKE_AGENT = "Orchestrator"
DATASET_MISTAKE_STEP = 9
ROSTER = (ORCHESTRATOR, WEB_SURFER)
SPEAKER_NAME = "WebSurfer"
MAX_TURNS = 20
MAX_STALLS = 3


def gold_record(
    query: Dict[str, Any],
    *,
    final_answer: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build an unlabeled gold record for one free-loop run.

    Args:
        query:
            Query id and text.
        final_answer:
            Answer the orchestrator stated, when the run produced one.
        run_id:
            Session run id, when the session has one.

    Returns:
        Empty who and when labels, the reference answer, and the dataset label.
    """
    return {
        "gold_who": None,
        "gold_when": None,
        "rule": "Label who and when from this run before scoring.",
        "query": {"id": query.get("id"), "text": query.get("text")},
        "mode": "free_loop",
        "roster": list(ROSTER),
        "reference_answer": REFERENCE_ANSWER,
        "final_answer": final_answer,
        "dataset_label": {
            "source": "Who&When hand-crafted 36",
            "mistake_agent": DATASET_MISTAKE_AGENT,
            "mistake_step": DATASET_MISTAKE_STEP,
        },
        "run_id": run_id,
    }
