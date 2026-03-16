"""Interpretability analysis: explanation retrieval, decision summaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ._resolve import resolve_run


def _record_to_dict(record: Any) -> Dict[str, Any]:
    """Convert a SimpleRecord to a dict for JSON-friendly return values."""
    return {
        "id": record.id,
        "kind": record.kind,
        "actor": getattr(record, "actor", "?"),
        "timestamp": getattr(record, "timestamp", ""),
        "payload": record.payload,
        "provenance": getattr(record, "provenance", None) or {},
        "accountability": getattr(record, "accountability", None) or {},
    }


def get_explanations_for(
    record_id: str,
    run_id: str,
    *,
    output_base: str = "./output",
    write_output: bool = False,
) -> List[Dict[str, Any]]:
    """Retrieve the explanation and decision records that explain or justify the given record.

    **What it means:** An "explanation" for a record is the set of decision or
    explanation records that led to it or that document why it exists. For
    example, for an outcome record, the explanations are the agent_update
    (decision) records that produced the actions for that step, and any
    explicit explanation records attached to the run. This supports
    interpretability: answering "why did this happen?" for a given state or
    outcome.

    **How it works:** The method loads the run's records and finds those that
    are linked to the given record_id — e.g. via trace enabled_by_id (which
    agent_update enabled this transition), provenance derived_from, or
    explanation record references. It returns a structured list or dict of
    those records (or their IDs and payloads) so callers can present or
    summarise them. When write_output is True, writes the list to
    output_base/run_id/analysis/interpretability/explanations_for_last.json.

    Args:
        record_id: The record to get explanations for (e.g. an outcome id).
        run_id: Run identifier (same as the run's output folder name).
        output_base: Base directory for run folders; default "./output".
        write_output: If True, write JSON to output_base/run_id/analysis/interpretability/.

    Returns:
        A list of decision/explanation records as dicts (id, kind, actor,
        timestamp, payload, ...). Includes agent_update records that are
        linked via outcome provenance derived_from or trace enabled_by_id,
        and any explanation records that reference those decisions. Sorted by
        timestamp.

    Raises:
        FileNotFoundError: If run metadata or records are not found.
    """
    resolved = resolve_run(run_id, output_base=output_base)
    outcomes = list(resolved.inspect("outcome"))
    traces = list(resolved.inspect("trace"))
    agent_updates = list(resolved.inspect("agent_update"))
    explanations = list(resolved.inspect("explanation"))

    agent_update_by_id = {r.id: r for r in agent_updates}
    outcome_by_id = {r.id: r for r in outcomes}
    explanation_by_decision_id: Dict[str, Any] = {}
    for r in explanations:
        did = r.payload.get("decision_id") if isinstance(r.payload, dict) else None
        if did:
            explanation_by_decision_id.setdefault(did, []).append(r)

    seen_ids: set = set()
    result: List[Dict[str, Any]] = []

    def add_record(rec: Any, role: str = "") -> None:
        if rec is None or rec.id in seen_ids:
            return
        seen_ids.add(rec.id)
        d = _record_to_dict(rec)
        if role:
            d["_role"] = role
        result.append(d)

    # Outcome: provenance.derived_from lists agent_update ids that created this outcome
    target_outcome = outcome_by_id.get(record_id)
    if target_outcome is not None:
        prov = getattr(target_outcome, "provenance", None) or {}
        if isinstance(prov, dict):
            for did in prov.get("derived_from", []):
                add_record(agent_update_by_id.get(did), "derived_from")
                for ex in explanation_by_decision_id.get(did, []):
                    add_record(ex, "explanation")

    # Traces that point to this record: enabled_by_id is the agent_update that enabled the transition
    for trace in traces:
        payload = trace.payload if hasattr(trace, "payload") else {}
        if not isinstance(payload, dict) or payload.get("to_id") != record_id:
            continue
        enabled_by = payload.get("enabled_by_id")
        if enabled_by:
            add_record(agent_update_by_id.get(enabled_by), "enabled_transition")
            for ex in explanation_by_decision_id.get(enabled_by, []):
                add_record(ex, "explanation")

    result.sort(key=lambda d: (d.get("timestamp", ""), d.get("id", "")))

    if write_output:
        out_dir = Path(output_base) / run_id / "analysis" / "interpretability"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "explanations_for_last.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)

    return result
