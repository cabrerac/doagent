"""Tests for doagent.analysis run resolution (resolve_run, inspect-style access)."""

import json
import tempfile
from pathlib import Path

from doagent.analysis._resolve import _load_metadata, resolve_run


def test_load_metadata_finds_file():
    """_load_metadata reads metadata.json from output_base/run_id/."""
    with tempfile.TemporaryDirectory() as tmp:
        run_id = "gridworld_run_20260315_120000_abc123"
        run_path = Path(tmp) / run_id
        run_path.mkdir(parents=True)
        meta = {"run_id": run_id, "scenario_name": "gridworld", "storage_type": "file", "metadata_schema_version": 1}
        (run_path / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
        loaded = _load_metadata(run_id, tmp)
        assert loaded["run_id"] == run_id
        assert loaded["storage_type"] == "file"


def test_resolve_run_file_backed_inspect():
    """resolve_run returns an object with inspect(kind) for file-backed runs."""
    with tempfile.TemporaryDirectory() as tmp:
        run_id = "push_run_20260315_120000_def456"
        run_path = Path(tmp) / run_id
        records_dir = run_path / "records"
        records_dir.mkdir(parents=True)
        meta = {
            "run_id": run_id,
            "scenario_name": "push",
            "storage_type": "file",
            "metadata_schema_version": 1,
            "records_dir": "records",
        }
        (run_path / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
        # Empty records; inspect should return []
        resolved = resolve_run(run_id, output_base=tmp)
        outcomes = resolved.inspect("outcome")
        assert outcomes == []
        traces = resolved.inspect("trace")
        assert traces == []
