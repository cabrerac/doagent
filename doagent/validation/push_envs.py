"""Simple push environment wrapper for validation."""

from __future__ import annotations

from typing import Any, Dict

from .environment import ParallelEnvWrapper, ValidationEnv


def _make_pettingzoo_mpe_env(env_name: str, params: Dict[str, Any]) -> ValidationEnv:
    """Create a PettingZoo MPE2 parallel environment and wrap it."""
    try:
        import importlib
    except ImportError as exc:
        raise ImportError(
            "PettingZoo is required for MPE2 environments. "
            "Install with: pip install pettingzoo"
        ) from exc
    try:
        env_fn = importlib.import_module(f"mpe2.{env_name}")
        env = env_fn.parallel_env(**params)
        return ParallelEnvWrapper(env)
    except ImportError as exc:
        raise ImportError(
            f"PettingZoo MPE2 env '{env_name}' not found. "
            "Install with: pip install pettingzoo"
        ) from exc


def make_push_env(env_name: str, params: Dict[str, Any]) -> ValidationEnv:
    """Create a simple push environment by name."""
    if env_name.startswith("pettingzoo:mpe2:"):
        mpe_name = env_name.split("pettingzoo:mpe2:", 1)[1]
        return _make_pettingzoo_mpe_env(mpe_name, params)
    if env_name.startswith("pettingzoo:mpe:"):
        mpe_name = env_name.split("pettingzoo:mpe:", 1)[1]
        return _make_pettingzoo_mpe_env(mpe_name, params)

    raise ValueError(
        f"Unknown simple push environment '{env_name}'. "
        "Use 'pettingzoo:mpe2:<env>' or 'pettingzoo:mpe:<env>' or provide a custom wrapper."
    )
