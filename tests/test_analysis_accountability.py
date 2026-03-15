"""Tests for doagent.analysis.accountability (causal_attribution, render_attribution_charts)."""

import json
import tempfile
from pathlib import Path

from doagent.analysis import accountability


def _write_jsonl(path: Path, records: list) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def _minimal_run(tmp: str, run_id: str = "attr_run_test") -> Path:
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


def test_causal_attribution_returns_structure():
    """causal_attribution returns dict with agents, agent_discovered, productive, redundant, etc."""
    with tempfile.TemporaryDirectory() as tmp:
        records_dir = _minimal_run(tmp)
        o0 = {
            "id": "initial_state",
            "timestamp": "2026-03-15T12:00:00Z",
            "actor": "env",
            "kind": "outcome",
            "payload": {"round": 0, "observations": {"a": {"cells": [{"x": 0, "y": 0}]}}},
            "provenance": {},
            "accountability": {},
        }
        o1 = {
            "id": "outcome-1",
            "timestamp": "2026-03-15T12:00:01Z",
            "actor": "env",
            "kind": "outcome",
            "payload": {
                "round": 1,
                "observations": {
                    "a": {"cells": [{"x": 0, "y": 0}, {"x": 1, "y": 0}]},
                },
            },
            "provenance": {},
            "accountability": {},
        }
        t1 = {
            "id": "trace-1",
            "timestamp": "2026-03-15T12:00:01Z",
            "actor": "a",
            "kind": "trace",
            "payload": {"from_id": "initial_state", "to_id": "outcome-1", "enabled_by_id": "au1", "round": 1},
            "provenance": {},
            "accountability": {},
        }
        _write_jsonl(records_dir / "outcome.jsonl", [o0, o1])
        _write_jsonl(records_dir / "trace.jsonl", [t1])
        _write_jsonl(records_dir / "agent_update.jsonl", [])

        attr = accountability.causal_attribution("attr_run_test", output_base=tmp)
        assert "agents" in attr
        assert "agent_discovered" in attr
        assert "agent_productive" in attr
        assert "agent_redundant" in attr
        assert "per_round_cumulative" in attr
        assert "max_round" in attr
        assert "a" in attr["agents"]
        assert len(attr["agent_discovered"].get("a", set())) >= 1  # (1,0) newly discovered
        assert attr["agent_productive"].get("a", 0) >= 1


def test_causal_attribution_empty_traces():
    """causal_attribution with no traces returns empty agents and zero counts."""
    with tempfile.TemporaryDirectory() as tmp:
        records_dir = _minimal_run(tmp)
        o1 = {"id": "outcome-1", "timestamp": "2026-03-15T12:00:00Z", "actor": "env", "kind": "outcome", "payload": {"round": 1}, "provenance": {}, "accountability": {}}
        _write_jsonl(records_dir / "outcome.jsonl", [o1])
        _write_jsonl(records_dir / "trace.jsonl", [])
        _write_jsonl(records_dir / "agent_update.jsonl", [])

        attr = accountability.causal_attribution("attr_run_test", output_base=tmp)
        assert attr["agents"] == []
        assert attr["max_round"] == 0


def test_render_attribution_charts_writes_file():
    """render_attribution_charts writes a PNG when output_path is a file."""
    with tempfile.TemporaryDirectory() as tmp:
        records_dir = _minimal_run(tmp)
        o1 = {"id": "outcome-1", "timestamp": "2026-03-15T12:00:00Z", "actor": "env", "kind": "outcome", "payload": {"round": 1, "observations": {"a": {"cells": [{"x": 0, "y": 0}]}}}, "provenance": {}, "accountability": {}}
        t1 = {"id": "trace-1", "timestamp": "2026-03-15T12:00:00Z", "actor": "a", "kind": "trace", "payload": {"from_id": "initial_state", "to_id": "outcome-1", "round": 1}, "provenance": {}, "accountability": {}}
        _write_jsonl(records_dir / "outcome.jsonl", [o1])
        _write_jsonl(records_dir / "trace.jsonl", [t1])
        _write_jsonl(records_dir / "agent_update.jsonl", [])

        attr = accountability.causal_attribution("attr_run_test", output_base=tmp)
        out_file = Path(tmp) / "attribution.png"
        accountability.render_attribution_charts(attr, str(out_file))
        assert out_file.is_file()
        assert out_file.stat().st_size > 0


def test_render_attribution_charts_writes_to_directory():
    """render_attribution_charts writes causal_attribution.png/.pdf when output_path is a directory."""
    with tempfile.TemporaryDirectory() as tmp:
        attr = {
            "agents": ["agent_0"],
            "agent_discovered": {"agent_0": {(0, 0), (1, 0)}},
            "agent_productive": {"agent_0": 2},
            "agent_redundant": {"agent_0": 0},
            "per_round_cumulative": {1: {"agent_0": 1}, 2: {"agent_0": 2}},
            "global_known": {(0, 0), (1, 0)},
            "max_round": 2,
        }
        out_dir = Path(tmp) / "charts"
        accountability.render_attribution_charts(attr, str(out_dir))
        assert (out_dir / "causal_attribution.png").is_file()
        assert (out_dir / "causal_attribution.pdf").is_file()
