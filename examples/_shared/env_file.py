"""Load KEY=VALUE pairs from a .env file into the process environment.

A missing file is a no-op.
Existing environment variables are not overwritten.
"""

from __future__ import annotations

import os
from pathlib import Path


def default_env_path() -> Path:
    """Return the .env path at the repository root."""
    return Path(__file__).resolve().parents[2] / ".env"


def load_dotenv(path: str | Path | None = None) -> None:
    """Read KEY=VALUE lines from a .env file into the process environment.

    Blank lines and comments that start with # are skipped.
    An optional export prefix on a line is ignored.
    Surrounding single or double quotes on a value are stripped.
    A key already present in the environment is left unchanged.
    A missing file does nothing.

    Args:
        path:
            File to read. Defaults to .env at the repository root.
    """
    env_path = Path(path) if path is not None else default_env_path()
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key not in os.environ:
            os.environ[key] = value
