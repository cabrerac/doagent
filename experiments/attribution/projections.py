"""D-level views and lookup from one DOAgent run.

This module downsamples native D2 records to D0 and D1, and recovers the planted checker fault.
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
    """Return the input and output of an agent decision, if present."""
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
    """Downsample a D2 record list to the fields a live D0 or D1 run would keep."""
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
    """Find a checker that accepted a reported value known to be wrong.

    This is an explicit rule for the addition example, not a general
    attribution algorithm. It uses structured fields already present in D.
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
    """Build D0, D1, D2, and lookup output from a completed Session."""
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
    """Write D0, D1, D2, and lookup JSON under a run's analysis folder."""
    artifacts = build_attribution_artifacts(session)
    output_dir = Path(run_path) / "analysis" / "attribution"
    output_dir.mkdir(parents=True, exist_ok=True)

    paths: Dict[str, str] = {}
    for name, value in artifacts.items():
        path = output_dir / f"{name}.json"
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        paths[name] = str(path)
    return paths
