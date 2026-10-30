"""Time one Hidden Profile run and count model tokens.

A scripted player does not call a model, so the token count is zero.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import tempfile
import time

from experiments.information_flow.hidden_profile.run_doagent import run_session
from experiments.information_flow.hidden_profile.run_marble import run_marble


@dataclass(frozen=True)
class RunCost:
    """Time and tokens for one recording setting.

    Args:
        name: Recording setting.
        seconds: Middle time of the timed runs, in seconds.
        tokens: Model tokens used by the players.
    """

    name: str
    seconds: float
    tokens: int


def median(values: Sequence[float]) -> float:
    """Return the middle value of a list of numbers.

    Args:
        values: Numbers to summarise.

    Returns:
        The middle value.
        An even count uses the average of the two middle values.

    Raises:
        ValueError: The list is empty.
    """
    if not values:
        raise ValueError("values must not be empty")
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def repeated_cost(
    name: str,
    action: Callable[[], None],
    repeats: int = 5,
) -> RunCost:
    """Warm up once, then return the middle time of several runs.

    Args:
        name: Recording setting.
        action: Call that plays one fresh run.
        repeats: How many timed runs follow the warm-up.

    Returns:
        The middle time and a token count of zero.

    Raises:
        ValueError: The repeat count is not a positive integer.
    """
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1:
        raise ValueError("repeats must be a positive integer")
    action()
    samples = []
    for _repeat in range(repeats):
        started = time.perf_counter()
        action()
        samples.append(time.perf_counter() - started)
    return RunCost(name, median(samples), 0)


def measure_hidden_profile(repeats: int = 5) -> tuple[RunCost, ...]:
    """Time each DOAgent logging level and each MARBLE view.

    Each setting is warmed up once, then timed in a fresh folder.

    Args:
        repeats: How many timed runs follow the warm-up.

    Returns:
        One cost row per setting.

    Raises:
        ValueError: The repeat count is not a positive integer.
    """
    rows = [
        repeated_cost(name, _session_action(level), repeats)
        for level, name in ((0, "D0"), (1, "D1"), (2, "D2"))
    ]
    rows.append(repeated_cost("S1", _marble_action("S1", "HiddenProfileEnv.log"), repeats))
    rows.append(
        repeated_cost(
            "Sk",
            _marble_action(
                "Sk",
                ("HiddenProfileEnv.log", "HiddenProfileAgent.agent-a.log"),
            ),
            repeats,
        )
    )
    rows.append(repeated_cost("Sall", _marble_action("Sall", None), repeats))
    rows.append(repeated_cost("Sstructured", _marble_action("Sstructured", None), repeats))
    return tuple(rows)


def _session_action(logging_level: int) -> Callable[[], None]:
    """Return a call that plays one session in a fresh folder."""

    def action() -> None:
        with tempfile.TemporaryDirectory() as folder:
            run_session(17, logging_level, folder)

    return action


def _marble_action(
    condition: str,
    names: str | tuple[str, ...] | None,
) -> Callable[[], None]:
    """Return a call that plays one MARBLE view in a fresh folder."""

    def action() -> None:
        with tempfile.TemporaryDirectory() as folder:
            run_marble(17, folder, condition=condition, names=names)

    return action
