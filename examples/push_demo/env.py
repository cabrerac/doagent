"""Push environment factory for the push demo.

This is example code, not part of the doagent library. It creates a
PettingZoo MPE2 push environment wrapped via experiments.environment.ParallelEnvWrapper.
"""

from __future__ import annotations

import importlib
from typing import Any, Dict


def create_push_env(
    env_name: str = "simple_push_v3",
    max_cycles: int = 100,
    continuous_actions: bool = False,
    dynamic_rescaling: bool = False,
    render_mode: str | None = None,
    **kwargs: Any,
) -> Any:
    """Create a PettingZoo MPE2 push environment."""
    from experiments.environment import ParallelEnvWrapper

    params: Dict[str, Any] = {
        "max_cycles": max_cycles,
        "continuous_actions": continuous_actions,
        "dynamic_rescaling": dynamic_rescaling,
        **kwargs,
    }
    if render_mode:
        params["render_mode"] = render_mode

    try:
        env_fn = importlib.import_module(f"mpe2.{env_name}")
    except ImportError as exc:
        raise ImportError(
            f"PettingZoo MPE2 env '{env_name}' not found. "
            "Install with: pip install pettingzoo"
        ) from exc

    env = env_fn.parallel_env(**params)
    return ParallelEnvWrapper(env)
