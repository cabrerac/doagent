"""Tests for doagent.analysis.traceability (build_trace_graph, get_traces_to/from, render_trace_graph)."""

import json
import tempfile
from pathlib import Path

from doagent.analysis import traceability


def _write_jsonl(path: Path, records: list) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def _minimal_run(tmp: str, run_id: str = "trace_run_test") -> Path:
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


def test_build_trace_graph_returns_graph_with_nodes_and_edges():
    """build_trace_graph returns a MultiDiGraph with node_meta and expected structure."""
    with tempfile.TemporaryDirectory() as tmp:
        records_dir = _minimal_run(tmp)
        o1 = {
            "id": "outcome-1",
            "timestamp": "2026-03-15T12:00:00Z",
            "actor": "env",
            "kind": "outcome",
            "payload": {"round": 1, "rewards": {"a": 0}, "actions": {}},
            "provenance": {},
            "accountability": {},
        }
        au1 = {
            "id": "agent-update-1",
            "timestamp": "2026-03-15T12:00:00Z",
            "actor": "a",
            "kind": "agent_update",
            "payload": {"decision": {"response": {"decision": {"action": 0}}}},
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

        G = traceability.build_trace_graph("trace_run_test", output_base=tmp)
        assert G.number_of_nodes() >= 2  # initial_state + outcome-1
        assert G.number_of_edges() == 1
        assert "initial_state" in G.nodes()
        assert "outcome-1" in G.nodes()
        assert G.graph.get("node_meta")
        assert G.graph["node_meta"].get("outcome-1", {}).get("type") == "outcome"


def test_get_traces_to_returns_incoming_traces():
    """get_traces_to returns trace records whose to_id matches record_id."""
    with tempfile.TemporaryDirectory() as tmp:
        records_dir = _minimal_run(tmp)
        o1 = {"id": "outcome-1", "timestamp": "2026-03-15T12:00:00Z", "actor": "env", "kind": "outcome", "payload": {"round": 1}, "provenance": {}, "accountability": {}}
        t1 = {"id": "trace-1", "timestamp": "2026-03-15T12:00:00Z", "actor": "a", "kind": "trace", "payload": {"from_id": "initial_state", "to_id": "outcome-1", "round": 1}, "provenance": {}, "accountability": {}}
        _write_jsonl(records_dir / "outcome.jsonl", [o1])
        _write_jsonl(records_dir / "trace.jsonl", [t1])
        _write_jsonl(records_dir / "agent_update.jsonl", [])

        to_list = traceability.get_traces_to("outcome-1", "trace_run_test", output_base=tmp)
        assert len(to_list) == 1
        assert to_list[0]["id"] == "trace-1"
        assert to_list[0]["payload"]["to_id"] == "outcome-1"


def test_get_traces_from_returns_outgoing_traces():
    """get_traces_from returns trace records whose from_id matches record_id."""
    with tempfile.TemporaryDirectory() as tmp:
        records_dir = _minimal_run(tmp)
        o1 = {"id": "outcome-1", "timestamp": "2026-03-15T12:00:00Z", "actor": "env", "kind": "outcome", "payload": {"round": 1}, "provenance": {}, "accountability": {}}
        t1 = {"id": "trace-1", "timestamp": "2026-03-15T12:00:00Z", "actor": "a", "kind": "trace", "payload": {"from_id": "initial_state", "to_id": "outcome-1", "round": 1}, "provenance": {}, "accountability": {}}
        _write_jsonl(records_dir / "outcome.jsonl", [o1])
        _write_jsonl(records_dir / "trace.jsonl", [t1])
        _write_jsonl(records_dir / "agent_update.jsonl", [])

        from_list = traceability.get_traces_from("initial_state", "trace_run_test", output_base=tmp)
        assert len(from_list) == 1
        assert from_list[0]["payload"]["from_id"] == "initial_state"


def test_render_trace_graph_writes_png():
    """render_trace_graph writes a PNG file when output_path has .png extension."""
    with tempfile.TemporaryDirectory() as tmp:
        records_dir = _minimal_run(tmp)
        o1 = {"id": "outcome-1", "timestamp": "2026-03-15T12:00:00Z", "actor": "env", "kind": "outcome", "payload": {"round": 1}, "provenance": {}, "accountability": {}}
        _write_jsonl(records_dir / "outcome.jsonl", [o1])
        _write_jsonl(records_dir / "trace.jsonl", [])
        _write_jsonl(records_dir / "agent_update.jsonl", [])

        G = traceability.build_trace_graph("trace_run_test", output_base=tmp)
        out_file = Path(tmp) / "trace_graph.png"
        traceability.render_trace_graph(G, str(out_file))
        assert out_file.is_file()
        assert out_file.stat().st_size > 0


def test_render_trace_graph_writes_dot():
    """render_trace_graph writes a .dot file when output_path has .dot extension."""
    with tempfile.TemporaryDirectory() as tmp:
        records_dir = _minimal_run(tmp)
        o1 = {"id": "outcome-1", "timestamp": "2026-03-15T12:00:00Z", "actor": "env", "kind": "outcome", "payload": {"round": 1}, "provenance": {}, "accountability": {}}
        _write_jsonl(records_dir / "outcome.jsonl", [o1])
        _write_jsonl(records_dir / "trace.jsonl", [])
        _write_jsonl(records_dir / "agent_update.jsonl", [])

        G = traceability.build_trace_graph("trace_run_test", output_base=tmp)
        out_file = Path(tmp) / "trace_graph.dot"
        traceability.render_trace_graph(G, str(out_file))
        assert out_file.is_file()
        content = out_file.read_text(encoding="utf-8")
        assert "digraph" in content
        assert "outcome" in content or "S0" in content
