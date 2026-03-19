"""Tests for doagent.analysis.interpretability atomic explanations."""

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


def test_build_atomic_explanations_unknown_record_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        records_dir = _minimal_run(tmp)
        o1 = {"id": "outcome-1", "timestamp": "2026-03-19T12:00:00Z", "actor": "env", "kind": "outcome", "payload": {}, "provenance": {}, "accountability": {}}
        _write_jsonl(records_dir / "outcome.jsonl", [o1])
        _write_jsonl(records_dir / "trace.jsonl", [])
        _write_jsonl(records_dir / "agent_update.jsonl", [])

        units = interpretability.build_atomic_explanations("other-id", "interp_run_test", output_base=tmp)
        assert units == []


def test_build_atomic_explanations_level_1_from_trace_and_decision():
    with tempfile.TemporaryDirectory() as tmp:
        records_dir = _minimal_run(tmp)
        o1 = {"id": "outcome-1", "timestamp": "2026-03-19T12:00:00Z", "actor": "env", "kind": "outcome", "payload": {"round": 1}, "provenance": {}, "accountability": {}}
        au1 = {
            "id": "au1",
            "timestamp": "2026-03-19T12:00:00Z",
            "actor": "a",
            "kind": "agent_update",
            "payload": {"decision": {"request": {"context": {"round": 1}}, "response": {"decision": {"action": 2}}}},
            "provenance": {},
            "accountability": {},
        }
        t1 = {"id": "trace-1", "timestamp": "2026-03-19T12:00:00Z", "actor": "a", "kind": "trace", "payload": {"from_id": "initial_state", "to_id": "outcome-1", "enabled_by_id": "au1", "round": 1}, "provenance": {}, "accountability": {}}
        _write_jsonl(records_dir / "outcome.jsonl", [o1])
        _write_jsonl(records_dir / "agent_update.jsonl", [au1])
        _write_jsonl(records_dir / "trace.jsonl", [t1])

        units = interpretability.build_atomic_explanations("outcome-1", "interp_run_test", output_base=tmp)
        assert len(units) == 1
        u = units[0]
        assert u["level"] == 1
        assert u["decision_id"] == "au1"
        assert u["from_state_id"] == "initial_state"
        assert u["to_state_id"] == "outcome-1"
        assert "because" not in u["rendered_text"]


def test_build_atomic_explanations_level_2_with_explanation_record():
    with tempfile.TemporaryDirectory() as tmp:
        records_dir = _minimal_run(tmp)
        o1 = {
            "id": "outcome-1",
            "timestamp": "2026-03-19T12:00:00Z",
            "actor": "env",
            "kind": "outcome",
            "payload": {"round": 1},
            "provenance": {"derived_from": ["au1"]},
            "accountability": {},
        }
        au1 = {
            "id": "au1",
            "timestamp": "2026-03-19T12:00:00Z",
            "actor": "a",
            "kind": "agent_update",
            "payload": {"decision": {"request": {"context": {"round": 1}}, "response": {"decision": {"action": 4}}}},
            "provenance": {},
            "accountability": {},
        }
        t1 = {
            "id": "trace-1",
            "timestamp": "2026-03-19T12:00:01Z",
            "actor": "a",
            "kind": "trace",
            "payload": {"from_id": "s0", "to_id": "outcome-1", "enabled_by_id": "au1", "round": 1},
            "provenance": {},
            "accountability": {},
        }
        ex1 = {
            "id": "ex1",
            "timestamp": "2026-03-19T12:00:02Z",
            "actor": "a",
            "kind": "explanation",
            "payload": {"decision_id": "au1", "summary": "move toward frontier"},
            "provenance": {},
            "accountability": {},
        }
        _write_jsonl(records_dir / "outcome.jsonl", [o1])
        _write_jsonl(records_dir / "agent_update.jsonl", [au1])
        _write_jsonl(records_dir / "trace.jsonl", [t1])
        _write_jsonl(records_dir / "explanation.jsonl", [ex1])

        units = interpretability.build_atomic_explanations(
            "outcome-1", "interp_run_test", output_base=tmp, write_output=True
        )
        assert len(units) == 1
        u = units[0]
        assert u["level"] == 2
        assert u["rationale_text"] == "move toward frontier"
        assert "because" in u["rendered_text"]
        out = Path(tmp) / "interp_run_test" / "analysis" / "interpretability" / "atomic_explanations_for_last.json"
        assert out.exists()
