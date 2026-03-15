"""Tests for doagent.analysis.provenance (walk_chain, render_chain_tree)."""

import json
import tempfile
from pathlib import Path

from doagent.analysis import provenance


def _write_jsonl(path: Path, records: list) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def test_walk_chain_last_empty_run_raises():
    """walk_chain with record_id='last' and no outcomes raises ValueError."""
    with tempfile.TemporaryDirectory() as tmp:
        run_id = "provenance_run_test"
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
        # No outcome.jsonl
        with open(records_dir / "outcome.jsonl", "w"):
            pass
        try:
            provenance.walk_chain("last", run_id, output_base=tmp)
        except ValueError as e:
            assert "No outcome" in str(e)
        else:
            assert False, "expected ValueError"


def test_walk_chain_returns_structured_tree():
    """walk_chain returns a nested dict with record_id, kind, depth, summary, children."""
    with tempfile.TemporaryDirectory() as tmp:
        run_id = "provenance_run_test"
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
        o1 = {
            "id": "outcome-1",
            "timestamp": "2026-03-15T12:00:00Z",
            "actor": "env",
            "kind": "outcome",
            "payload": {"round": 1, "rewards": {"a": 0}, "actions": {"a": 0}},
            "provenance": {},
            "accountability": {},
        }
        au1 = {
            "id": "agent-update-1",
            "timestamp": "2026-03-15T12:00:00Z",
            "actor": "a",
            "kind": "agent_update",
            "payload": {"decision": {"response": {"decision": {"action": 0}}, "request": {"goal": "test"}}},
            "provenance": {},
            "accountability": {},
        }
        t1 = {
            "id": "trace-1",
            "timestamp": "2026-03-15T12:00:00Z",
            "actor": "a",
            "kind": "trace",
            "payload": {"from_id": "initial_state", "to_id": "outcome-1", "enabled_by_id": "agent-update-1", "round": 1},
            "provenance": {},
            "accountability": {},
        }
        _write_jsonl(records_dir / "outcome.jsonl", [o1])
        _write_jsonl(records_dir / "agent_update.jsonl", [au1])
        _write_jsonl(records_dir / "trace.jsonl", [t1])

        tree = provenance.walk_chain("last", run_id, output_base=tmp, max_depth=5)
        assert tree["record_id"] == "outcome-1"
        assert tree["kind"] == "outcome"
        assert "round=1" in tree["summary"]
        assert isinstance(tree["children"], list)
        # Should have trace as child (incoming trace)
        trace_children = [c for c in tree["children"] if c.get("kind") == "trace"]
        assert len(trace_children) == 1
        assert trace_children[0]["record_id"] == "trace-1"
        assert len(trace_children[0]["children"]) >= 1  # enabled_by and/or from_state


def test_walk_chain_from_specific_record_id():
    """walk_chain with explicit record_id uses that record as root."""
    with tempfile.TemporaryDirectory() as tmp:
        run_id = "provenance_run_test"
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
        o1 = {
            "id": "outcome-1",
            "timestamp": "2026-03-15T12:00:00Z",
            "actor": "env",
            "kind": "outcome",
            "payload": {"round": 1},
            "provenance": {},
            "accountability": {},
        }
        _write_jsonl(records_dir / "outcome.jsonl", [o1])
        _write_jsonl(records_dir / "trace.jsonl", [])
        _write_jsonl(records_dir / "agent_update.jsonl", [])

        tree = provenance.walk_chain("outcome-1", run_id, output_base=tmp)
        assert tree["record_id"] == "outcome-1"
        assert tree["kind"] == "outcome"


def test_render_chain_tree_writes_file():
    """render_chain_tree produces a file at output_path."""
    with tempfile.TemporaryDirectory() as tmp:
        run_id = "provenance_run_test"
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
        o1 = {
            "id": "outcome-1",
            "timestamp": "2026-03-15T12:00:00Z",
            "actor": "env",
            "kind": "outcome",
            "payload": {"round": 1},
            "provenance": {},
            "accountability": {},
        }
        _write_jsonl(records_dir / "outcome.jsonl", [o1])
        _write_jsonl(records_dir / "trace.jsonl", [])
        _write_jsonl(records_dir / "agent_update.jsonl", [])

        out_file = Path(tmp) / "chain.png"
        provenance.render_chain_tree("outcome-1", run_id, str(out_file), output_base=tmp)
        assert out_file.is_file()
        assert out_file.stat().st_size > 0
