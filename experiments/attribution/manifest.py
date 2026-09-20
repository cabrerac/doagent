"""Lab notes for one attribution experiment run.

It records which code and settings produced a measured result.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def git_commit(repo_root: Optional[Path] = None) -> Optional[str]:
    """Return HEAD if this is a git checkout, otherwise None."""
    cwd = repo_root or Path(__file__).resolve().parents[2]
    try:
        value = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    commit = value.strip()
    return commit or None


def config_hash(config: Dict[str, Any]) -> str:
    """Stable fingerprint of the measured settings."""
    payload = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_run_manifest(
    *,
    run_id: Optional[str],
    storage: str,
    query: Dict[str, Any],
    plant: Dict[str, Any],
    logging_level: int,
    output_base: str,
) -> Dict[str, Any]:
    """Describe one addition-team run for later tables and checks."""
    config = {
        "storage": storage,
        "query": query,
        "plant": plant,
        "logging_level": logging_level,
        "output_base": output_base,
    }
    return {
        "run_id": run_id,
        "git_commit": git_commit(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": config,
        "config_hash": config_hash(config),
    }


def write_run_manifest(run_path: str | Path, manifest: Dict[str, Any]) -> str:
    """Write ``manifest.json`` next to gold and records."""
    path = Path(run_path) / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return str(path)
