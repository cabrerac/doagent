"""Run configuration for validation scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LoggingLevel = Literal[0, 1, 2]
LOGGING_LEVEL_0: LoggingLevel = 0
LOGGING_LEVEL_1: LoggingLevel = 1
LOGGING_LEVEL_2: LoggingLevel = 2
DEFAULT_LOGGING_LEVEL: LoggingLevel = 2


def _validate_logging_level(level: int) -> LoggingLevel:
    """Validate and return logging level. Raises ValueError if invalid."""
    if level not in (0, 1, 2):
        raise ValueError(
            f"logging_level must be 0, 1, or 2; got {level!r}"
        )
    return level  # type: ignore[return-value]


@dataclass(frozen=True)
class RunConfig:
    """Configuration for a validation run.

    Attributes:
        logging_level: 0 = agent_update + outcome (no trace, no provenance,
            no explanation); 1 = + trace + provenance + accountability on
            envelope; 2 = + decision.explanation + decision.response.reasoning.
            Default: 2.
    """

    logging_level: LoggingLevel = DEFAULT_LOGGING_LEVEL

    def __post_init__(self) -> None:
        _validate_logging_level(self.logging_level)

    @classmethod
    def with_logging_level(cls, level: int) -> RunConfig:
        """Create a RunConfig with the given logging level."""
        return cls(logging_level=_validate_logging_level(level))


def should_write_trace(logging_level: int) -> bool:
    """Return True if trace records should be written (Level 1+)."""
    return logging_level >= 1


def should_include_provenance_accountability(logging_level: int) -> bool:
    """Return True if provenance and accountability belong on envelope (Level 1+)."""
    return logging_level >= 1


def should_include_explanation(logging_level: int) -> bool:
    """Return True if decision.explanation should be populated (Level 2)."""
    return logging_level >= 2


def should_include_reasoning(logging_level: int) -> bool:
    """Return True if decision.response.reasoning should be kept (Level 2)."""
    return logging_level >= 2
