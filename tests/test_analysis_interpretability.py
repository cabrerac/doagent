"""Tests for doagent.analysis.interpretability (get_explanations_for)."""

import json
import tempfile
from pathlib import Path

from doagent.analysis import interpretability


def _write_jsonl(path: Path, records: list) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def _minimal_run(tmp: str, run_id: str = "interp_run_test") -> Path:
    run_path = Path(tmp) / run_id
    records_dir = run_path / "records"
    records_dir.mkdir(parents=True)
    (run_path / "metadata.json").write_text(
        json.dumps({
            "run_id": run_id,
            "scenario_name": "test",
            "storage_type": "file",
            "metadata_schema_version": 1,
            "records_dir": "records",
        }),
        encoding="utf-8",
    )
    return records_dir


def test_get_explanations_for_outcome_via_trace_enabled_by():
    """get_explanations_for returns agent_update when trace to_id matches and has enabled_by_id."""
    with tempfile.TemporaryDirectory() as tmp:
        records_dir = _minimal_run(tmp)
        o1 = {"id": "outcome-1", "timestamp": "2026-03-15T12:00:00Z", "actor": "env", "kind": "outcome", "payload": {"round": 1}, "provenance": {}, "accountability": {}}
        au1 = {"id": "au1", "timestamp": "2026-03-15T12:00:00Z", "actor": "a", "kind": "agent_update", "payload": {"decision": {"action": 1}}, "provenance": {}, "accountability": {}}
        t1 = {"id": "trace-1", "timestamp": "2026-03-15T12:00:00Z", "actor": "a", "kind": "trace", "payload": {"from_id": "initial_state", "to_id": "outcome-1", "enabled_by_id": "au1", "round": 1}, "provenance": {}, "accountability": {}}
        _write_jsonl(records_dir / "outcome.jsonl", [o1])
        _write_jsonl(records_dir / "agent_update.jsonl", [au1])
        _write_jsonl(records_dir / "trace.jsonl", [t1])

        explanations = interpretability.get_explanations_for("outcome-1", "interp_run_test", output_base=tmp)
        assert len(explanations) >= 1
        ids = [e["id"] for e in explanations]
        assert "au1" in ids


def test_get_explanations_for_outcome_via_provenance_derived_from():
    """get_explanations_for returns agent_updates listed in outcome provenance derived_from."""
    with tempfile.TemporaryDirectory() as tmp:
        records_dir = _minimal_run(tmp)
        o1 = {"id": "outcome-1", "timestamp": "2026-03-15T12:00:00Z", "actor": "env", "kind": "outcome", "payload": {"round": 1}, "provenance": {"derived_from": ["au1", "au2"]}, "accountability": {}}
        au1 = {"id": "au1", "timestamp": "2026-03-15T12:00:00Z", "actor": "a", "kind": "agent_update", "payload": {}, "provenance": {}, "accountability": {}}
        au2 = {"id": "au2", "timestamp": "2026-03-15T12:00:00Z", "actor": "b", "kind": "agent_update", "payload": {}, "provenance": {}, "accountability": {}}
        _write_jsonl(records_dir / "outcome.jsonl", [o1])
        _write_jsonl(records_dir / "agent_update.jsonl", [au1, au2])
        _write_jsonl(records_dir / "trace.jsonl", [])

        explanations = interpretability.get_explanations_for("outcome-1", "interp_run_test", output_base=tmp)
        assert len(explanations) == 2
        ids = {e["id"] for e in explanations}
        assert ids == {"au1", "au2"}


def test_get_explanations_for_unknown_record_returns_empty():
    """get_explanations_for returns empty list when no traces or outcome link to record_id."""
    with tempfile.TemporaryDirectory() as tmp:
        records_dir = _minimal_run(tmp)
        o1 = {"id": "outcome-1", "timestamp": "2026-03-15T12:00:00Z", "actor": "env", "kind": "outcome", "payload": {}, "provenance": {}, "accountability": {}}
        _write_jsonl(records_dir / "outcome.jsonl", [o1])
        _write_jsonl(records_dir / "trace.jsonl", [])
        _write_jsonl(records_dir / "agent_update.jsonl", [])

        explanations = interpretability.get_explanations_for("other-id", "interp_run_test", output_base=tmp)
        assert explanations == []
