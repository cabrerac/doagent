"""Interpretability analysis: transition-level atomic explanations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ._resolve import resolve_run

def _decision_action(agent_update: Any) -> Any:
    payload = getattr(agent_update, "payload", {}) or {}
    decision = payload.get("decision", {}) if isinstance(payload, dict) else {}
    if not isinstance(decision, dict):
        return None
    response = decision.get("response", {})
    if not isinstance(response, dict):
        return None
    return (response.get("choice") or {}).get("action")


def _decision_round(agent_update: Any) -> Any:
    payload = getattr(agent_update, "payload", {}) or {}
    decision = payload.get("decision", {}) if isinstance(payload, dict) else {}
    if not isinstance(decision, dict):
        return None
    request = decision.get("request", {})
    if not isinstance(request, dict):
        return None
    context = request.get("context", {})
    if not isinstance(context, dict):
        return None
    return context.get("round")


def _rationale_text(
    agent_update: Any,
    explanations_by_decision_id: Dict[str, List[Any]],
) -> Optional[str]:
    linked = explanations_by_decision_id.get(getattr(agent_update, "id", ""), [])
    for ex in linked:
        payload = getattr(ex, "payload", {}) or {}
        if not isinstance(payload, dict):
            continue
        summary = payload.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
        details = payload.get("details")
        if isinstance(details, str) and details.strip():
            return details.strip()

    payload = getattr(agent_update, "payload", {}) or {}
    decision = payload.get("decision", {}) if isinstance(payload, dict) else {}
    if isinstance(decision, dict):
        response = decision.get("response", {})
        if isinstance(response, dict):
            explanation = response.get("explanation")
            if isinstance(explanation, str) and explanation.strip():
                return explanation.strip()
    return None


def render_atomic_explanation_text(unit: Dict[str, Any]) -> str:
    """Render one atomic explanation unit into stable human text.

    The text mirrors the canonical template:
    "System was at state <from>. Agent <agent> made decision <action>
    [because <rationale>]. As a result, the system ended at state <to>."
    """
    from_state = unit.get("from_state_id") or "unknown_state"
    to_state = unit.get("to_state_id") or "unknown_state"
    agent_id = unit.get("agent_id") or "unknown_agent"
    action = unit.get("decision_action")
    action_text = str(action) if action is not None else "unknown_action"
    rationale = unit.get("rationale_text")
    if rationale:
        return (
            f'System was at state {from_state}. Agent {agent_id} made decision {action_text} '
            f'because "{rationale}". As a result, the system ended at state {to_state}.'
        )
    return (
        f"System was at state {from_state}. Agent {agent_id} made decision {action_text}. "
        f"As a result, the system ended at state {to_state}."
    )


def build_atomic_explanations(
    record_id: str,
    run_id: str,
    *,
    output_base: str = "./output",
    write_output: bool = False,
) -> List[Dict[str, Any]]:
    """Build transition-level atomic explanations for a target record.

    What it does:
    - Resolves a run by `run_id` and reads `outcome`, `trace`, `agent_update`,
      and `explanation` records.
    - Constructs one atomic unit per interpreted transition into `record_id`:
      `from_state -> decision -> optional rationale -> to_state`.
    - Annotates each unit with `level`:
      - `1`: decision-link only (no explicit rationale text found)
      - `2`: rationale text found (from explanation records or decision response)
    - Produces both machine-friendly fields and `rendered_text`.

    Output file (optional):
    - When `write_output=True`, writes
      `output_base/run_id/analysis/interpretability/atomic_explanations_for_last.json`.
    """
    resolved = resolve_run(run_id, output_base=output_base)
    outcomes = list(resolved.inspect("outcome"))
    traces = list(resolved.inspect("trace"))
    agent_updates = list(resolved.inspect("agent_update"))
    explanations = list(resolved.inspect("explanation"))

    outcome_by_id = {r.id: r for r in outcomes}
    agent_update_by_id = {r.id: r for r in agent_updates}
    explanations_by_decision_id: Dict[str, List[Any]] = {}
    for ex in explanations:
        payload = getattr(ex, "payload", {}) or {}
        if not isinstance(payload, dict):
            continue
        did = payload.get("decision_id")
        if did:
            explanations_by_decision_id.setdefault(did, []).append(ex)

    derived_from_ids: set[str] = set()
    target_outcome = outcome_by_id.get(record_id)
    if target_outcome is not None:
        prov = getattr(target_outcome, "provenance", None) or {}
        if isinstance(prov, dict):
            for did in prov.get("derived_from", []):
                if isinstance(did, str):
                    derived_from_ids.add(did)

    units: List[Dict[str, Any]] = []
    seen_keys: set[tuple] = set()

    for trace in traces:
        payload = getattr(trace, "payload", {}) or {}
        if not isinstance(payload, dict):
            continue
        if payload.get("to_id") != record_id:
            continue
        decision_id = payload.get("enabled_by_id")
        if not isinstance(decision_id, str) or not decision_id:
            continue
        decision = agent_update_by_id.get(decision_id)
        if decision is None:
            continue

        linked_explanations = explanations_by_decision_id.get(decision_id, [])
        explanation_ids = [ex.id for ex in linked_explanations]
        rationale = _rationale_text(decision, explanations_by_decision_id)
        level = 2 if rationale else 1
        action = _decision_action(decision)
        round_id = payload.get("round")
        if round_id is None:
            round_id = _decision_round(decision)
        unit = {
            "run_id": run_id,
            "record_id": record_id,
            "round": round_id,
            "agent_id": getattr(decision, "actor", "unknown"),
            "from_state_id": payload.get("from_id"),
            "to_state_id": payload.get("to_id"),
            "decision_id": decision_id,
            "decision_action": action,
            "rationale_text": rationale,
            "level": level,
            "links": {
                "trace_id": getattr(trace, "id", ""),
                "enabled_by_id": decision_id,
                "relation": payload.get("relation"),
                "derived_from": decision_id in derived_from_ids,
                "explanation_ids": explanation_ids,
            },
            "evidence_refs": [
                ref for ref in ([getattr(trace, "id", ""), decision_id] + explanation_ids) if ref
            ],
        }
        unit["rendered_text"] = render_atomic_explanation_text(unit)

        key = (unit["decision_id"], unit["from_state_id"], unit["to_state_id"])
        if key not in seen_keys:
            seen_keys.add(key)
            units.append(unit)

    # Fallback: provenance-only decisions with no trace edge to record_id.
    for decision_id in sorted(derived_from_ids):
        key_any = any(u["decision_id"] == decision_id for u in units)
        if key_any:
            continue
        decision = agent_update_by_id.get(decision_id)
        if decision is None:
            continue
        linked_explanations = explanations_by_decision_id.get(decision_id, [])
        explanation_ids = [ex.id for ex in linked_explanations]
        rationale = _rationale_text(decision, explanations_by_decision_id)
        level = 2 if rationale else 1
        unit = {
            "run_id": run_id,
            "record_id": record_id,
            "round": _decision_round(decision),
            "agent_id": getattr(decision, "actor", "unknown"),
            "from_state_id": None,
            "to_state_id": record_id,
            "decision_id": decision_id,
            "decision_action": _decision_action(decision),
            "rationale_text": rationale,
            "level": level,
            "links": {
                "trace_id": None,
                "enabled_by_id": decision_id,
                "relation": None,
                "derived_from": True,
                "explanation_ids": explanation_ids,
            },
            "evidence_refs": [ref for ref in ([decision_id] + explanation_ids) if ref],
        }
        unit["rendered_text"] = render_atomic_explanation_text(unit)
        units.append(unit)

    units.sort(key=lambda u: (u.get("round") is None, u.get("round"), u.get("agent_id"), u.get("decision_id")))

    if write_output:
        out_dir = Path(output_base) / run_id / "analysis" / "interpretability"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "atomic_explanations_for_last.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(units, f, indent=2, default=str)

    return units
