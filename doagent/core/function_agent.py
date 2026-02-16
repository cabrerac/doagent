"""Function-backed agent adapter."""

from __future__ import annotations

from typing import Callable, Dict, Any
from uuid import uuid4

from ..interface.decision_agent import DecisionAgent
from ..interface.shared_data import SharedDataAdapter
from ..records import DecisionRequest, DecisionResponse
from .shared_data import new_record


class FunctionAgent(DecisionAgent):
    """Decision agent backed by a callable."""

    def __init__(
        self,
        name: str,
        shared_data: SharedDataAdapter,
        decide_fn: Callable[[DecisionRequest], DecisionResponse],
        *,
        decision_kind: str = "decision",
    ) -> None:
        """Initialise with a name, shared data adapter, and callable."""
        self._name = name
        self._shared_data = shared_data
        self._decide_fn = decide_fn
        self._decision_kind = decision_kind

    def decide(
        self,
        request: DecisionRequest,
        *,
        persist: bool = True,
    ) -> DecisionResponse:
        """Produce a decision response. Optionally persist as decision record."""
        response = dict(self._decide_fn(request))
        request_id = request.get("id")
        response_id = response.get("id") or str(uuid4())
        response_actor = response.get("actor") or self._name

        response.update(
            {
                "id": response_id,
                "request_id": response.get("request_id") or request_id,
                "actor": response_actor,
            }
        )

        if persist:
            response_clean = {k: v for k, v in response.items() if k not in ("provenance", "accountability")}
            payload: Dict[str, Any] = {
                "request": dict(request),
                "response": response_clean,
            }
            record_provenance = response.get("provenance") or request.get("provenance")
            record_accountability = response.get("accountability") or request.get("accountability")
            record = new_record(
                actor=response_actor,
                kind=self._decision_kind,
                payload=payload,
                provenance=record_provenance,
                accountability=record_accountability,
            )
            self._shared_data.write(record)
        return response
