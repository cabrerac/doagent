"""Generic environment factory for DOAgent.

Resolves an entry point (string or callable) and calls it with the given
params to create an environment instance. The library contains no
scenario-specific env code; all env creation logic lives in user/example code.
"""

from __future__ import annotations

import importlib
from typing import Any, Callable, Union


def make_env(entry_point: Union[str, Callable[..., Any]], **params: Any) -> Any:
    """Create an environment from an entry point.

    Args:
        entry_point: Either a callable that returns an env, or a string in
            the format "module.path:callable_name" that will be resolved
            via importlib.
        **params: Keyword arguments passed to the resolved callable.

    Returns:
        The environment instance returned by the callable.

    Examples::

        # String entry point (config-friendly, works in YAML)
        env = make_env("my_project.envs:create_grid", width=10, height=10)

        # Callable entry point (programmatic, type-safe)
        env = make_env(create_grid, width=10, height=10)
    """
    factory = _resolve_entry_point(entry_point)
    return factory(**params)


def _resolve_entry_point(entry_point: Union[str, Callable[..., Any]]) -> Callable[..., Any]:
    """Resolve an entry point to a callable."""
    if callable(entry_point):
        return entry_point

    if not isinstance(entry_point, str):
        raise TypeError(
            f"entry_point must be a string ('module:callable') or a callable; "
            f"got {type(entry_point).__name__}"
        )

    if ":" not in entry_point:
        raise ValueError(
            f"String entry_point must be in 'module.path:callable_name' format; "
            f"got {entry_point!r}"
        )

    module_path, attr_name = entry_point.rsplit(":", 1)
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ImportError(
            f"Could not import module {module_path!r} from entry point {entry_point!r}"
        ) from exc

    try:
        factory = getattr(module, attr_name)
    except AttributeError as exc:
        raise AttributeError(
            f"Module {module_path!r} has no attribute {attr_name!r} "
            f"(entry point: {entry_point!r})"
        ) from exc

    if not callable(factory):
        raise TypeError(
            f"Resolved entry point {entry_point!r} is not callable "
            f"(got {type(factory).__name__})"
        )

    return factory
