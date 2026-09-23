"""Build D0, D1, and D2 views and a lookup from one run.

D0 and D1 are thinner copies of the native records.
Lookup names a checker that accepted a wrong value.
"""

from __future__ import annotations

import copy
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from doagent.records import SimpleRecord


RUN_RECORD_KINDS = (
    "participation",
    "agent_update",
    "outcome",
    "trace",
    "explanation",
)
D0_KINDS = frozenset({"participation", "agent_update", "outcome"})
D1_KINDS = frozenset({"participation", "agent_update", "outcome", "trace"})


def _decision_step(record: SimpleRecord) -> Optional[Dict[str, Any]]:
    """Return the step fields of an agent decision.

    Args:
        record:
            One stored record.

    Returns:
        Step, record id, agent, input, and output.
        None when the record has no round decision.
    """
    decision = record.payload.get("decision") or {}
    request = decision.get("request")
    response = decision.get("response")
    if not isinstance(request, dict) or not isinstance(response, dict):
        return None

    context = request.get("context") or {}
    if "round" not in context:
        return None

    return {
        "step": context["round"],
        "record_id": record.id,
        "agent": record.actor,
        "input": request.get("inputs") or {},
        "output": response,
    }


def project_logging_level(
    records: Iterable[Dict[str, Any]],
    level: int,
) -> List[Dict[str, Any]]:
    """Keep the fields a live run at this logging level would store.

    Args:
        records:
            Native records from a level 2 run.
        level:
            Logging level, 0, 1, or 2.

    Returns:
        A copy of the records with fields outside that level removed.

    Raises:
        ValueError:
            If level is outside 0, 1, and 2.
    """
    if level not in (0, 1, 2):
        raise ValueError(f"logging_level must be 0, 1, or 2; got {level!r}")
    projected: List[Dict[str, Any]] = []
    for record in records:
        kind = record.get("kind")
        if level == 0 and kind not in D0_KINDS:
            continue
        if level == 1 and kind not in D1_KINDS:
            continue
        item = copy.deepcopy(record)
        if level < 2:
            payload = item.get("payload")
            if isinstance(payload, dict):
                decision = payload.get("decision")
                if isinstance(decision, dict):
                    decision.pop("explanation", None)
                    response = decision.get("response")
                    if isinstance(response, dict):
                        response.pop("reasoning", None)
        if level < 1:
            item["provenance"] = {}
            item["accountability"] = {}
        projected.append(item)
    return projected


def lookup_planted_failure(
    agent_updates: Iterable[SimpleRecord],
) -> Optional[Dict[str, Any]]:
    """Return the checker step that accepted a wrong value.

    Args:
        agent_updates:
            Agent decision records, in time order.

    Returns:
        Who, when, and the record id.
        None when no checker accepted a wrong value.
    """
    for record in agent_updates:
        step = _decision_step(record)
        if step is None:
            continue
        action = (
            (step["output"].get("choice") or {}).get("action")
            if isinstance(step["output"], dict)
            else None
        )
        if not isinstance(action, dict) or action.get("type") != "check":
            continue
        if (
            action.get("accept") is True
            and "reported" in action
            and "correct" in action
            and action["reported"] != action["correct"]
        ):
            return {
                "who": record.actor,
                "when": step["step"],
                "record_id": record.id,
                "rule": "checker accepted a reported value that differs from the correct value",
            }
    return None


def build_attribution_artifacts(session: Any) -> Dict[str, Any]:
    """Build D0, D1, D2, and lookup from a finished session.

    Args:
        session:
            Session whose records are already written.

    Returns:
        The three views and the lookup result.
    """
    records: List[SimpleRecord] = []
    for kind in RUN_RECORD_KINDS:
        records.extend(session.inspect(kind))
    records.sort(key=lambda record: (record.timestamp, record.id))

    agent_updates = [
        record for record in records if record.kind == "agent_update"
    ]
    native = [asdict(record) for record in records]
    return {
        "d0": project_logging_level(native, 0),
        "d1": project_logging_level(native, 1),
        "d2": native,
        "lookup": lookup_planted_failure(agent_updates),
    }


def write_attribution_artifacts(
    session: Any,
    run_path: str | Path,
) -> Dict[str, str]:
    """Write D0, D1, D2, and lookup JSON under the run folder.

    Args:
        session:
            Session whose records are already written.
        run_path:
            Folder that holds the run.

    Returns:
        Written path for each artifact.
    """
    artifacts = build_attribution_artifacts(session)
    output_dir = Path(run_path) / "analysis" / "attribution"
    output_dir.mkdir(parents=True, exist_ok=True)

    paths: Dict[str, str] = {}
    for name, value in artifacts.items():
        path = output_dir / f"{name}.json"
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        paths[name] = str(path)
    return paths
