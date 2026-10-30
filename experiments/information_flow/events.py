"""Define representation-independent events for information-flow experiments."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ExecutionEvent:
    """Identify and order one event in a controlled execution.

    Args:
        episode_id: Identifier of the episode containing the event.
        event_id: Identifier of this event.
        logical_step: Non-negative model time within the episode.
        sequence_index: Non-negative total event position within the episode.

    Raises:
        ValueError: An identifier is empty or an event position is invalid.
    """

    episode_id: str
    event_id: str
    logical_step: int
    sequence_index: int

    def __post_init__(self) -> None:
        """Validate the event fields."""
        identifiers = (self.episode_id, self.event_id)
        if any(not isinstance(value, str) or not value for value in identifiers):
            raise ValueError("event identifiers must be non-empty strings")
        positions = (self.logical_step, self.sequence_index)
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in positions
        ):
            raise ValueError("event positions must be non-negative integers")


@dataclass(frozen=True)
class StateTruth(ExecutionEvent):
    """Store one private latent state for the environment and scorer.

    Args:
        state: Latent categorical state.
        random_draw: Optional unit-interval draw that selected the state.
        previous_state_event_id: Optional identifier of the previous state truth.

    Raises:
        ValueError: The state, random draw, or previous identifier is invalid.
    """

    state: str
    random_draw: float | None = None
    previous_state_event_id: str | None = None

    def __post_init__(self) -> None:
        """Validate the private state fields."""
        super().__post_init__()
        if not isinstance(self.state, str) or not self.state:
            raise ValueError("state must be a non-empty string")
        if self.random_draw is not None and (
            not math.isfinite(self.random_draw)
            or self.random_draw < 0.0
            or self.random_draw >= 1.0
        ):
            raise ValueError("random_draw must be finite and in the interval [0, 1)")
        if self.previous_state_event_id is not None and (
            not isinstance(self.previous_state_event_id, str)
            or not self.previous_state_event_id
        ):
            raise ValueError("previous_state_event_id must be a non-empty string")


@dataclass(frozen=True)
class ObservationEvent(ExecutionEvent):
    """Describe one observation offered to an agent and every recorder.

    Args:
        agent_id: Identifier of the observing agent.
        observation: Categorical value observed by the agent.
        channel_id: Identifier of the observation channel configuration.
        source_state_event_id: Private state identifier used for provenance.

    Raises:
        ValueError: An observation field is not a non-empty string.
    """

    agent_id: str
    observation: str
    channel_id: str
    source_state_event_id: str

    def __post_init__(self) -> None:
        """Validate the observation fields."""
        super().__post_init__()
        values = (
            self.agent_id,
            self.observation,
            self.channel_id,
            self.source_state_event_id,
        )
        if any(not isinstance(value, str) or not value for value in values):
            raise ValueError("observation fields must be non-empty strings")


@dataclass(frozen=True)
class MessageDeliveryEvent(ExecutionEvent):
    """Describe one message delivery produced by the controlled environment.

    Args:
        sender_id: Identifier of the sending agent.
        message_id: Identifier of the delivered message.
        message: Categorical message value.
        recipient_ids: Agents that actually received the message.

    Raises:
        ValueError: A message field or recipient set is invalid.
    """

    sender_id: str
    message_id: str
    message: str
    recipient_ids: frozenset[str]

    def __post_init__(self) -> None:
        """Validate the message-delivery fields."""
        super().__post_init__()
        values = (self.sender_id, self.message_id, self.message)
        if any(not isinstance(value, str) or not value for value in values):
            raise ValueError("message fields must be non-empty strings")
        if not isinstance(self.recipient_ids, frozenset) or any(
            not isinstance(recipient_id, str) or not recipient_id
            for recipient_id in self.recipient_ids
        ):
            raise ValueError("recipient_ids must be a frozenset of non-empty strings")


@dataclass(frozen=True)
class BeliefEvent(ExecutionEvent):
    """Describe one probability distribution reported by an agent.

    Args:
        agent_id: Identifier of the reporting agent.
        state_labels: Ordered categorical state values.
        probabilities: Reported probability for each state value.
        input_event_ids: Events supplied before the belief was reported.

    Raises:
        ValueError: A belief field or probability distribution is invalid.
    """

    agent_id: str
    state_labels: tuple[str, ...]
    probabilities: tuple[float, ...]
    input_event_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate the reported belief."""
        super().__post_init__()
        if not isinstance(self.agent_id, str) or not self.agent_id:
            raise ValueError("agent_id must be a non-empty string")
        if (
            not isinstance(self.state_labels, tuple)
            or not self.state_labels
            or any(not isinstance(label, str) or not label for label in self.state_labels)
            or len(set(self.state_labels)) != len(self.state_labels)
        ):
            raise ValueError("state_labels must contain unique non-empty strings")
        if (
            not isinstance(self.probabilities, tuple)
            or len(self.probabilities) != len(self.state_labels)
            or any(
                not math.isfinite(probability)
                or probability < 0.0
                or probability > 1.0
                for probability in self.probabilities
            )
            or not math.isclose(
                math.fsum(self.probabilities),
                1.0,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            raise ValueError("probabilities must match the states and sum to one")
        _validate_event_identifiers(self.input_event_ids, "input_event_ids")


@dataclass(frozen=True)
class ActionEvent(ExecutionEvent):
    """Describe one categorical action selected by an agent.

    Args:
        agent_id: Identifier of the acting agent.
        action: Categorical action selected by the agent.
        input_event_ids: Events supplied before the action was selected.

    Raises:
        ValueError: An action field or input identifier is invalid.
    """

    agent_id: str
    action: str
    input_event_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate the action fields."""
        super().__post_init__()
        values = (self.agent_id, self.action)
        if any(not isinstance(value, str) or not value for value in values):
            raise ValueError("action fields must be non-empty strings")
        _validate_event_identifiers(self.input_event_ids, "input_event_ids")


@dataclass(frozen=True)
class TransitionEvent(ExecutionEvent):
    """Record the inputs and state links for one environment step.

    Args:
        action_event_id: Identifier of the action applied in the step.
        input_event_ids: Identifiers of the other events supplied to the step.
        previous_state_event_id: Identifier of the private state before the step.
        next_state_event_id: Identifier of the private state after the step.

    Raises:
        ValueError: An identifier is empty, repeated, or not a string.
    """

    action_event_id: str
    input_event_ids: tuple[str, ...]
    previous_state_event_id: str
    next_state_event_id: str | None = None

    def __post_init__(self) -> None:
        """Validate the transition fields."""
        super().__post_init__()
        if not isinstance(self.action_event_id, str) or not self.action_event_id:
            raise ValueError("action_event_id must be a non-empty string")
        _validate_event_identifiers(self.input_event_ids, "input_event_ids")
        if (
            not isinstance(self.previous_state_event_id, str)
            or not self.previous_state_event_id
        ):
            raise ValueError("previous_state_event_id must be a non-empty string")
        if self.next_state_event_id is not None and (
            not isinstance(self.next_state_event_id, str)
            or not self.next_state_event_id
        ):
            raise ValueError("next_state_event_id must be a non-empty string")


@dataclass(frozen=True)
class OutcomeEvent(ExecutionEvent):
    """Describe one public result produced from an agent action.

    Args:
        agent_id: Identifier of the agent receiving the result.
        outcome: Categorical result value.
        action_event_id: Action event evaluated by the environment.
        contributing_event_ids: Events named as producing this result.
            Empty when the result does not name them.

    Raises:
        ValueError: An outcome field is not a non-empty string.
    """

    agent_id: str
    outcome: str
    action_event_id: str
    contributing_event_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate the outcome fields."""
        super().__post_init__()
        values = (self.agent_id, self.outcome, self.action_event_id)
        if any(not isinstance(value, str) or not value for value in values):
            raise ValueError("outcome fields must be non-empty strings")
        _validate_event_identifiers(self.contributing_event_ids, "contributing_event_ids")


RecorderInputEvent = (
    ObservationEvent
    | MessageDeliveryEvent
    | BeliefEvent
    | ActionEvent
    | OutcomeEvent
)


def recipient_set_query(event: MessageDeliveryEvent) -> frozenset[str]:
    """Return the true recipient set used to score an audience query."""
    return event.recipient_ids


def _validate_event_identifiers(values: tuple[str, ...], name: str) -> None:
    """Validate an immutable sequence of unique event identifiers."""
    if (
        not isinstance(values, tuple)
        or any(not isinstance(value, str) or not value for value in values)
        or len(set(values)) != len(values)
    ):
        raise ValueError(f"{name} must contain unique non-empty strings")
