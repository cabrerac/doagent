"""Record one model call as a prompt and an output.

The export is written by the call itself.
A later reading does not run the game again.
Record ids are refused, so a trace cannot lean on store links.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from pathlib import Path

_RECORD_ID = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


class ModelTrace:
    """Append one JSON line for each model call.

    Args:
        path: File that receives the lines.
    """

    def __init__(self, path: str | Path) -> None:
        """Create or replace the trace file."""
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("w", encoding="utf-8")

    def close(self) -> None:
        """Close the trace file."""
        self._handle.close()

    def write_call(self, prompt: str, output: str) -> None:
        """Store one completed call.

        Args:
            prompt: Text sent to the model.
            output: Text returned by the model.

        Raises:
            ValueError: The prompt or the output contains a record id.
        """
        reject_record_ids(prompt)
        reject_record_ids(output)
        self._line({"prompt": prompt, "output": output})

    def write_blocked(self, prompt: str, kind: str) -> None:
        """Store a call that a provider limit stopped.

        Args:
            prompt: Text that was about to be sent.
            kind: rate_limit or context_limit.

        Raises:
            ValueError: The prompt contains a record id, or the kind is unknown.
        """
        if kind not in ("rate_limit", "context_limit"):
            raise ValueError("kind must be rate_limit or context_limit")
        reject_record_ids(prompt)
        self._line({"prompt": prompt, "output": "", "blocked": kind})

    def _line(self, payload: Mapping[str, str]) -> None:
        """Append one JSON object and flush it."""
        self._handle.write(json.dumps(payload, sort_keys=True) + "\n")
        self._handle.flush()


def reject_record_ids(text: str) -> None:
    """Refuse text that contains a record id.

    Args:
        text: Prompt, output, or rendered trace.

    Raises:
        ValueError: A UUID record id is present.
    """
    if _RECORD_ID.search(text):
        raise ValueError("a trace must not contain a record id")


def limit_kind(exc: BaseException) -> str | None:
    """Classify a provider failure that should be stored.

    Args:
        exc: Exception raised by the model caller.

    Returns:
        rate_limit, context_limit, or None when the failure is something else.
    """
    status = getattr(exc, "status_code", None)
    text = str(exc).lower()
    if status == 429 or "rate limit" in text or "too many requests" in text:
        return "rate_limit"
    if (
        "context length" in text
        or "context window" in text
        or "maximum context" in text
        or "token limit" in text
    ):
        return "context_limit"
    return None


def recorded_call(
    caller: Callable[[str], str],
    prompt: str,
    trace: ModelTrace,
) -> str:
    """Call the model once and store the prompt and the output.

    A rate limit or a context limit is stored, then raised again.
    The game does not need a second run to recover that fact.

    Args:
        caller: Function that sends one prompt and returns the output text.
        prompt: Text sent to the model.
        trace: Export that receives the call.

    Returns:
        The model output.

    Raises:
        ValueError: The prompt or the output contains a record id.
        Exception: The caller failed.
            Limit failures are stored before they propagate.
    """
    reject_record_ids(prompt)
    try:
        output = caller(prompt)
    except Exception as exc:
        kind = limit_kind(exc)
        if kind is None:
            raise
        trace.write_blocked(prompt, kind)
        raise
    trace.write_call(prompt, output)
    return output


def decision_prompt(observation: Mapping[str, object]) -> str:
    """Build one decision prompt from an observation.

    Args:
        observation: Fields the agent is allowed to see.

    Returns:
        The prompt text.

    Raises:
        ValueError: The observation text contains a record id.
    """
    body = json.dumps(observation, sort_keys=True, default=str)
    reject_record_ids(body)
    return "Observation:\n" + body + "\nReply with the chosen action."
