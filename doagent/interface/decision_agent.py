"""Model-agnostic agent interface."""

from __future__ import annotations

from typing import Protocol

from ..records import DecisionRequest, DecisionResponse


class DecisionAgent(Protocol):
    """Protocol for model-agnostic decision agents."""

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        """Produce a decision response for a request."""
