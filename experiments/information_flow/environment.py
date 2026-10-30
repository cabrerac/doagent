"""Provide signalling rules and a scripted episode loop."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random

from .events import (
    ActionEvent,
    BeliefEvent,
    MessageDeliveryEvent,
    ObservationEvent,
    OutcomeEvent,
    RecorderInputEvent,
    StateTruth,
)


@dataclass(frozen=True)
class ObservationChannel:
    """Configure one agent's symmetric observation channel.

    Args:
        agent_id: Identifier of the observing agent.
        accuracy: Probability that the observation equals the hidden state.

    Raises:
        ValueError: The identifier or probability is invalid.
    """

    agent_id: str
    accuracy: float

    def __post_init__(self) -> None:
        """Validate the observation channel."""
        if not isinstance(self.agent_id, str) or not self.agent_id:
            raise ValueError("agent_id must be a non-empty string")
        if (
            not math.isfinite(self.accuracy)
            or self.accuracy < 0.0
            or self.accuracy > 1.0
        ):
            raise ValueError("accuracy must be finite and in the interval [0, 1]")


@dataclass(frozen=True)
class EnvironmentConfig:
    """Configure one round of the controlled signalling environment.

    Args:
        states: Ordered hidden-state alphabet.
        observation_channels: Symmetric observation channel for each agent.
        sender_id: Agent whose observation becomes the message.
        recipient_ids: Agents eligible to receive the message.
        delivery_probability: Independent delivery probability for each recipient.

    Raises:
        ValueError: A state, agent, topology, or probability is invalid.
    """

    states: tuple[str, ...]
    observation_channels: tuple[ObservationChannel, ...]
    sender_id: str
    recipient_ids: tuple[str, ...]
    delivery_probability: float

    def __post_init__(self) -> None:
        """Validate the environment configuration."""
        if (
            not isinstance(self.states, tuple)
            or len(self.states) < 2
            or any(not isinstance(state, str) or not state for state in self.states)
            or len(set(self.states)) != len(self.states)
        ):
            raise ValueError("states must contain at least two unique non-empty strings")
        if (
            not isinstance(self.observation_channels, tuple)
            or len(self.observation_channels) < 3
        ):
            raise ValueError("observation_channels must configure at least three agents")
        agent_ids = tuple(
            channel.agent_id
            for channel in self.observation_channels
        )
        if len(set(agent_ids)) != len(agent_ids):
            raise ValueError("observation channel agent identifiers must be unique")
        if self.sender_id not in agent_ids:
            raise ValueError("sender_id must identify a configured agent")
        if (
            not isinstance(self.recipient_ids, tuple)
            or not self.recipient_ids
            or len(set(self.recipient_ids)) != len(self.recipient_ids)
            or any(
                recipient_id not in agent_ids or recipient_id == self.sender_id
                for recipient_id in self.recipient_ids
            )
        ):
            raise ValueError("recipient_ids must identify unique non-sender agents")
        if (
            not math.isfinite(self.delivery_probability)
            or self.delivery_probability < 0.0
            or self.delivery_probability > 1.0
        ):
            raise ValueError(
                "delivery_probability must be finite and in the interval [0, 1]"
            )


@dataclass(frozen=True)
class ControlledEpisode:
    """Hold private truth and recorder-visible events for one episode."""

    seed: int
    truth: StateTruth
    events: tuple[RecorderInputEvent, ...]


DEFAULT_CONFIG = EnvironmentConfig(
    states=("amber", "blue", "green", "red"),
    observation_channels=(
        ObservationChannel("agent-a", 0.85),
        ObservationChannel("agent-b", 0.70),
        ObservationChannel("agent-c", 0.55),
    ),
    sender_id="agent-a",
    recipient_ids=("agent-b", "agent-c"),
    delivery_probability=0.5,
)


class SignallingRules:
    """Run one signalling round and keep the hidden colour private.

    Args:
        config: State, observation, communication, and agent configuration.
    """

    def __init__(self, config: EnvironmentConfig = DEFAULT_CONFIG) -> None:
        """Store the configuration and wait for a seed."""
        self.config = config
        self._random_source: random.Random | None = None
        self._phase = "new"
        self._events: list[RecorderInputEvent] = []
        self._truth: StateTruth | None = None
        self._sequence_index = 1
        self._glimpses: dict[str, str] = {}
        self._observation_event_ids: dict[str, str] = {}
        self._message_event: MessageDeliveryEvent | None = None
        self._episode_id = ""
        self.seed: int | None = None

    def reset(self, *, seed: int) -> dict[str, dict[str, str]]:
        """Draw the hidden colour and return one glimpse per agent.

        Args:
            seed: Integer seed controlling all random choices.

        Returns:
            One observation mapping per agent.

        Raises:
            ValueError: The seed is not an integer.
        """
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        self.seed = seed
        self._random_source = random.Random(seed)
        self._phase = "send"
        self._events = []
        self._sequence_index = 1
        self._message_event = None
        self._episode_id = f"episode-{seed}"
        state_draw = self._random_source.random()
        state_index = min(
            int(state_draw * len(self.config.states)),
            len(self.config.states) - 1,
        )
        hidden_state = self.config.states[state_index]
        self._truth = StateTruth(
            episode_id=self._episode_id,
            event_id="state-0",
            logical_step=0,
            sequence_index=0,
            state=hidden_state,
            random_draw=state_draw,
        )
        self._glimpses = {}
        self._observation_event_ids = {}
        for channel in self.config.observation_channels:
            glimpse = _sample_observation(
                self._random_source,
                hidden_state,
                self.config.states,
                channel.accuracy,
            )
            event_id = f"observation-{channel.agent_id}"
            self._glimpses[channel.agent_id] = glimpse
            self._observation_event_ids[channel.agent_id] = event_id
            self._events.append(
                ObservationEvent(
                    episode_id=self._episode_id,
                    event_id=event_id,
                    logical_step=0,
                    sequence_index=self._sequence_index,
                    agent_id=channel.agent_id,
                    observation=glimpse,
                    channel_id=f"symmetric-{channel.accuracy:g}",
                    source_state_event_id=self._truth.event_id,
                )
            )
            self._sequence_index += 1
        return {
            agent_id: {"phase": "send", "observation": glimpse}
            for agent_id, glimpse in self._glimpses.items()
        }

    def step(self, actions: dict[str, dict[str, object]]) -> dict[str, dict]:
        """Deliver the sender message, or score the reported decisions.

        Args:
            actions: Agent identifier to that agent's action mapping.

        Returns:
            Observations, rewards, and a finished flag for each agent.

        Raises:
            ValueError: The phase or an action mapping is invalid.
        """
        if self._phase == "send":
            return self._deliver(actions)
        if self._phase == "decide":
            return self._score(actions)
        raise ValueError("reset the rules before stepping")

    def episode(self) -> ControlledEpisode:
        """Return the private truth and the ordered event stream.

        Returns:
            The completed episode.

        Raises:
            ValueError: The episode has not been scored.
        """
        if self._phase != "done" or self._truth is None or self.seed is None:
            raise ValueError("the episode is incomplete")
        return ControlledEpisode(
            seed=self.seed,
            truth=self._truth,
            events=tuple(self._events),
        )

    def _deliver(self, actions: dict[str, dict[str, object]]) -> dict[str, dict]:
        """Deliver the sender message and open the decision phase."""
        if self._random_source is None or self._truth is None:
            raise ValueError("reset the rules before stepping")
        if set(actions) != {self.config.sender_id}:
            raise ValueError("the send step accepts only the sender action")
        action = actions[self.config.sender_id]
        message = action.get("message")
        if action.get("kind") != "send" or not isinstance(message, str) or not message:
            raise ValueError("the sender action must name a non-empty message")
        delivered_recipients = frozenset(
            recipient_id
            for recipient_id in self.config.recipient_ids
            if self._random_source.random() < self.config.delivery_probability
        )
        self._message_event = MessageDeliveryEvent(
            episode_id=self._episode_id,
            event_id="message-0",
            logical_step=0,
            sequence_index=self._sequence_index,
            sender_id=self.config.sender_id,
            message_id="message-0",
            message=message,
            recipient_ids=delivered_recipients,
        )
        self._events.append(self._message_event)
        self._sequence_index += 1
        self._phase = "decide"
        observations = {
            agent_id: {
                "phase": "decide",
                "observation": glimpse,
                "message": (
                    message if agent_id in delivered_recipients else None
                ),
            }
            for agent_id, glimpse in self._glimpses.items()
        }
        agent_ids = tuple(self._glimpses)
        return {
            "observations": observations,
            "rewards": {agent_id: 0.0 for agent_id in agent_ids},
            "done": {agent_id: False for agent_id in agent_ids},
        }

    def _score(self, actions: dict[str, dict[str, object]]) -> dict[str, dict]:
        """Record reported beliefs and score the chosen colours."""
        if self._truth is None or self._message_event is None:
            raise ValueError("reset the rules before stepping")
        agent_ids = tuple(
            channel.agent_id for channel in self.config.observation_channels
        )
        if set(actions) != set(agent_ids):
            raise ValueError("the decide step requires one action per agent")
        belief_event_ids: dict[str, str] = {}
        chosen: dict[str, str] = {}
        for agent_id in agent_ids:
            action = actions[agent_id]
            probabilities = action.get("probabilities")
            colour = action.get("action")
            if (
                action.get("kind") != "decide"
                or not isinstance(probabilities, tuple)
                or not isinstance(colour, str)
                or colour not in self.config.states
            ):
                raise ValueError("each decision must name a belief and a state")
            input_event_ids = [self._observation_event_ids[agent_id]]
            if agent_id in self._message_event.recipient_ids:
                input_event_ids.append(self._message_event.event_id)
            event_id = f"belief-{agent_id}"
            belief_event_ids[agent_id] = event_id
            self._events.append(
                BeliefEvent(
                    episode_id=self._episode_id,
                    event_id=event_id,
                    logical_step=0,
                    sequence_index=self._sequence_index,
                    agent_id=agent_id,
                    state_labels=self.config.states,
                    probabilities=probabilities,
                    input_event_ids=tuple(input_event_ids),
                )
            )
            self._sequence_index += 1
            chosen[agent_id] = colour
        action_event_ids: dict[str, str] = {}
        for agent_id in agent_ids:
            event_id = f"action-{agent_id}"
            action_event_ids[agent_id] = event_id
            self._events.append(
                ActionEvent(
                    episode_id=self._episode_id,
                    event_id=event_id,
                    logical_step=0,
                    sequence_index=self._sequence_index,
                    agent_id=agent_id,
                    action=chosen[agent_id],
                    input_event_ids=(belief_event_ids[agent_id],),
                )
            )
            self._sequence_index += 1
        rewards: dict[str, float] = {}
        observations: dict[str, dict[str, object]] = {}
        for agent_id in agent_ids:
            outcome = (
                "correct"
                if chosen[agent_id] == self._truth.state
                else "incorrect"
            )
            rewards[agent_id] = 1.0 if outcome == "correct" else 0.0
            self._events.append(
                OutcomeEvent(
                    episode_id=self._episode_id,
                    event_id=f"outcome-{agent_id}",
                    logical_step=0,
                    sequence_index=self._sequence_index,
                    agent_id=agent_id,
                    outcome=outcome,
                    action_event_id=action_event_ids[agent_id],
                )
            )
            self._sequence_index += 1
            message = (
                self._message_event.message
                if agent_id in self._message_event.recipient_ids
                else None
            )
            observations[agent_id] = {
                "phase": "done",
                "observation": self._glimpses[agent_id],
                "message": message,
                "outcome": outcome,
            }
        self._phase = "done"
        return {
            "observations": observations,
            "rewards": rewards,
            "done": {agent_id: True for agent_id in agent_ids},
        }


def run_episode(
    seed: int,
    config: EnvironmentConfig = DEFAULT_CONFIG,
) -> ControlledEpisode:
    """Run one reproducible round with the scripted signalling policy.

    Args:
        seed: Integer seed controlling all random choices.
        config: State, observation, communication, and agent configuration.

    Returns:
        Private state truth and an ordered recorder-visible event stream.

    Raises:
        ValueError: The seed is not an integer.
    """
    from .policies import signalling_policy

    rules = SignallingRules(config)
    observations = rules.reset(seed=seed)
    policies = {
        agent_id: signalling_policy(agent_id, config)
        for agent_id in observations
    }
    delivered = rules.step(
        {
            config.sender_id: policies[config.sender_id](
                observations[config.sender_id]
            )
        }
    )
    rules.step(
        {
            agent_id: policies[agent_id](observation)
            for agent_id, observation in delivered["observations"].items()
        }
    )
    return rules.episode()


def _sample_observation(
    random_source: random.Random,
    hidden_state: str,
    states: tuple[str, ...],
    accuracy: float,
) -> str:
    """Sample one value from a symmetric categorical observation channel."""
    if random_source.random() < accuracy:
        return hidden_state
    alternatives = tuple(state for state in states if state != hidden_state)
    return random_source.choice(alternatives)
