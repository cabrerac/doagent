"""Create an environment from a callable or an import path.

make_env resolves the entry point and calls it with the given params.
Scenario environments live in user code.
"""

from __future__ import annotations

import importlib
from typing import Any, Callable, Union


def make_env(entry_point: Union[str, Callable[..., Any]], **params: Any) -> Any:
    """Create an environment from an entry point.

    Args:
        entry_point:
            A callable, or a string of the form module.path:callable_name.
        **params:
            Keyword arguments passed to that callable.

    Returns:
        The environment instance.

    Raises:
        TypeError:
            If entry_point is neither a string nor a callable.
            Also raised when the resolved object is not callable.
        ValueError:
            If a string entry point contains no colon.
        ImportError:
            If the named module cannot be imported.
        AttributeError:
            If the module has no attribute with that name.
    """
    factory = _resolve_entry_point(entry_point)
    return factory(**params)


def _resolve_entry_point(entry_point: Union[str, Callable[..., Any]]) -> Callable[..., Any]:
    """Resolve an entry point to a callable.

    Args:
        entry_point:
            A callable, or a string of the form module.path:callable_name.

    Returns:
        The callable that creates the environment.

    Raises:
        TypeError:
            If entry_point is neither a string nor a callable.
            Also raised when the resolved object is not callable.
        ValueError:
            If a string entry point contains no colon.
        ImportError:
            If the named module cannot be imported.
        AttributeError:
            If the module has no attribute with that name.
    """
    if callable(entry_point):
        return entry_point

    if not isinstance(entry_point, str):
        raise TypeError(
            "entry_point must be a string of the form module:callable, or a callable. "
            f"Got {type(entry_point).__name__}."
        )

    if ":" not in entry_point:
        raise ValueError(
            "A string entry point must use the form module.path:callable_name. "
            f"Got {entry_point!r}."
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
