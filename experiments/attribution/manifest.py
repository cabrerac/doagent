"""Record the code version and settings for one attribution run."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def git_commit(repo_root: Optional[Path] = None) -> Optional[str]:
    """Return the current git commit hash.

    Args:
        repo_root:
            Repository to inspect.
            The project root is used when this is omitted.

    Returns:
        The HEAD commit hash.
        None when git cannot be read.
    """
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
    """Hash the measured settings.

    Args:
        config:
            Settings to fingerprint.

    Returns:
        A SHA-256 hex digest of the settings, with keys in a stable order.
    """
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
    """Build the manifest for one addition-team run.

    Args:
        run_id:
            Identifier of the run.
        storage:
            Storage name, such as memory or file.
        query:
            The numbers to add, as a and b.
        plant:
            Optional plant_wrong_sum and plant_accept_wrong.
        logging_level:
            Session recording level, 0, 1, or 2.
        output_base:
            Root folder for the run.

    Returns:
        Run id, git commit, creation time, config, and config hash.
    """
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
    """Write manifest.json in the run folder.

    Args:
        run_path:
            Folder that holds the run.
        manifest:
            Manifest mapping to write.

    Returns:
        Path of the written file.
    """
    path = Path(run_path) / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return str(path)
