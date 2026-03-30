"""Lightweight tool-call trace collector for policy factorization.

Used internally by SessionAgent.decide() to wrap per-agent tools and
capture their invocations as structured reasoning steps.  Not part of
the public API — users configure tools via agent configs and the
session handles the rest.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional


class _TraceCollector:
    """Accumulates tool-call steps during a single decide() invocation."""

    def __init__(self) -> None:
        self._steps: List[Dict[str, Any]] = []

    def wrap(self, name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Return a traced version of *fn* that records each call."""
        steps = self._steps

        def traced(*args: Any, **kwargs: Any) -> Any:
            inputs: Dict[str, Any] = {}
            if args:
                inputs["args"] = _safe_serialize(args)
            if kwargs:
                inputs["kwargs"] = _safe_serialize(kwargs)

            t0 = time.monotonic()
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                elapsed = time.monotonic() - t0
                steps.append({
                    "kind": "tool",
                    "name": name,
                    "inputs": inputs,
                    "error": str(exc),
                    "elapsed_s": round(elapsed, 4),
                })
                raise
            elapsed = time.monotonic() - t0
            steps.append({
                "kind": "tool",
                "name": name,
                "inputs": inputs,
                "output": _safe_serialize(result),
                "elapsed_s": round(elapsed, 4),
            })
            return result

        return traced

    @property
    def steps(self) -> List[Dict[str, Any]]:
        return self._steps

    def to_dict(self) -> Dict[str, Any]:
        """Serialize accumulated steps into the reasoning schema."""
        return {"steps": list(self._steps)}


def _safe_serialize(obj: Any, *, max_depth: int = 3) -> Any:
    """Best-effort serialization for trace I/O.  Truncates deeply nested
    or non-JSON-friendly objects to keep records manageable."""
    if max_depth <= 0:
        return repr(obj)
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _safe_serialize(v, max_depth=max_depth - 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(v, max_depth=max_depth - 1) for v in obj]
    return repr(obj)


def merge_reasoning(
    policy_reasoning: Optional[Dict[str, Any]],
    tool_reasoning: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Merge policy-provided reasoning with tool-captured reasoning.

    Returns None if neither source has content.
    """
    has_policy = policy_reasoning is not None and bool(policy_reasoning)
    has_tools = tool_reasoning is not None and bool(tool_reasoning.get("steps"))

    if has_policy and has_tools:
        merged = dict(policy_reasoning)  # type: ignore[arg-type]
        merged["tool_steps"] = tool_reasoning["steps"]  # type: ignore[index]
        return merged
    if has_policy:
        return policy_reasoning
    if has_tools:
        return tool_reasoning
    return None
