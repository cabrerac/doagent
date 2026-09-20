"""On-demand views over stored records.

decision_steps builds a compact step list when a caller asks for one.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Iterable, List, Optional


def _as_dict(record: Any) -> Dict[str, Any]:
    """Return a record as a plain dict.

    Args:
        record:
            A dict or an object with record fields.

    Returns:
        A dict with id, actor, kind, payload, and provenance when present.
    """
    if isinstance(record, dict):
        return record
    if is_dataclass(record):
        return asdict(record)
    return {
        "id": getattr(record, "id", None),
        "actor": getattr(record, "actor", None),
        "kind": getattr(record, "kind", None),
        "payload": getattr(record, "payload", {}) or {},
        "provenance": getattr(record, "provenance", {}) or {},
    }


def _payload(record: Dict[str, Any]) -> Dict[str, Any]:
    """Return the payload mapping of a record.

    Args:
        record:
            Record dict.

    Returns:
        The payload dict, or an empty dict if it is missing or not a mapping.
    """
    payload = record.get("payload") or {}
    return payload if isinstance(payload, dict) else {}


def _decision(record: Dict[str, Any]) -> Dict[str, Any]:
    """Return the decision mapping stored on a record.

    Args:
        record:
            Record dict.

    Returns:
        The decision dict, or an empty dict if it is missing or not a mapping.
    """
    decision = _payload(record).get("decision") or {}
    return decision if isinstance(decision, dict) else {}


def _round_id(record: Dict[str, Any]) -> Optional[int]:
    """Return the decision round stored on a record.

    Args:
        record:
            Record dict.

    Returns:
        The round integer, or None if the record has no round.
    """
    context = (_decision(record).get("request") or {}).get("context") or {}
    if isinstance(context, dict) and isinstance(context.get("round"), int):
        return context["round"]
    payload_round = _payload(record).get("round")
    if isinstance(payload_round, int):
        return payload_round
    return None


def _step_label(agent: str, step: int) -> str:
    """Return a readable label for one decision.

    Args:
        agent:
            Agent id.
        step:
            Decision round.

    Returns:
        A string of the form agent@step.
    """
    return f"{agent}@{step}"


def _output_and_explanation(
    decision: Dict[str, Any],
) -> tuple[Any, Optional[str]]:
    """Return the action output and any explanation on a decision.

    Args:
        decision:
            Decision mapping from a record payload.

    Returns:
        The action when present, otherwise the response.
        The second value is the explanation string, or None.
    """
    response = decision.get("response") or {}
    if not isinstance(response, dict):
        return response, None
    choice = response.get("choice")
    action = choice.get("action") if isinstance(choice, dict) else None
    output = action if action is not None else response
    explanation = decision.get("explanation")
    if not isinstance(explanation, str) or not explanation.strip():
        explanation = response.get("explanation")
    if isinstance(explanation, str) and explanation.strip():
        return output, explanation.strip()
    return output, None


def _label_index(records: List[Dict[str, Any]]) -> Dict[str, str]:
    """Map record ids to readable step or outcome labels.

    Args:
        records:
            Native record dicts.

    Returns:
        A dict from record id to a label such as solver@1 or outcome@0.
    """
    labels: Dict[str, str] = {}
    for record in records:
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            continue
        kind = record.get("kind")
        step = _round_id(record)
        if kind == "agent_update" and step is not None:
            labels[record_id] = _step_label(str(record.get("actor") or "unknown"), step)
        elif kind == "outcome" and step is not None:
            labels[record_id] = f"outcome@{step}"
    return labels


def _links_for_record(
    record: Dict[str, Any],
    labels: Dict[str, str],
    traces: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Return readable links that point at or from one decision.

    Args:
        record:
            Decision record dict.
        labels:
            Map from record id to a readable label.
        traces:
            Trace record dicts from the same run.

    Returns:
        Link dicts with relation and optional from and to labels.
    """
    links: List[Dict[str, str]] = []
    record_id = record.get("id")
    provenance = record.get("provenance") or {}
    sources = provenance.get("derived_from") if isinstance(provenance, dict) else None
    if isinstance(sources, list):
        for source in sources:
            label = labels.get(source)
            if label:
                links.append({"from": label, "relation": "derived_from"})
    if not isinstance(record_id, str):
        return links
    for trace in traces:
        payload = _payload(trace)
        if payload.get("enabled_by_id") != record_id:
            continue
        item: Dict[str, str] = {
            "relation": str(payload.get("relation") or "enables"),
        }
        from_label = labels.get(payload.get("from_id"))
        to_label = labels.get(payload.get("to_id"))
        if from_label:
            item["from"] = from_label
        if to_label:
            item["to"] = to_label
        links.append(item)
    return links


def decision_steps(
    records: Iterable[Any],
    *,
    level: int = 0,
) -> List[Dict[str, Any]]:
    """Project stored records into compact decision steps.

    Participation records are omitted.
    Outcome copies are omitted.
    Level 0 keeps step, agent, input, and output.
    Level 1 adds readable links.
    Level 2 adds the explanation when one was recorded.

    Args:
        records:
            Stored records as dicts or record objects.
        level:
            0, 1, or 2.

    Returns:
        One dict per scored decision, sorted by step.

    Raises:
        ValueError:
            If level is not 0, 1, or 2.
    """
    if level not in (0, 1, 2):
        raise ValueError(f"level must be 0, 1, or 2, got {level!r}")
    native = [_as_dict(record) for record in records]
    labels = _label_index(native)
    traces = [record for record in native if record.get("kind") == "trace"]
    steps: List[Dict[str, Any]] = []
    for record in native:
        if record.get("kind") != "agent_update":
            continue
        step = _round_id(record)
        if step is None:
            continue
        decision = _decision(record)
        request = decision.get("request") or {}
        inputs = request.get("inputs") if isinstance(request, dict) else {}
        output, explanation = _output_and_explanation(decision)
        item: Dict[str, Any] = {
            "step": step,
            "agent": record.get("actor"),
            "input": inputs if isinstance(inputs, dict) else {},
            "output": output,
        }
        if level >= 1:
            links = _links_for_record(record, labels, traces)
            if links:
                item["links"] = links
        if level >= 2 and explanation:
            item["explanation"] = explanation
        steps.append(item)
    steps.sort(key=lambda item: item["step"])
    return steps
