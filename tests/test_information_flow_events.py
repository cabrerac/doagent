"""Verify neutral events against the three-agent delivery experiment."""

from dataclasses import FrozenInstanceError
import math
import unittest

from experiments.information_flow.channels import build_joint_distribution
from experiments.information_flow.events import (
    MessageDeliveryEvent,
    ObservationEvent,
    StateTruth,
    TransitionEvent,
    recipient_set_query,
)
from experiments.information_flow.metrics import (
    conditional_entropy,
    mutual_information,
)


AGENTS = ("A", "B", "C")
OUTCOMES = ("000", "001", "010", "011", "100", "101", "110", "111")


def _delivery_event(outcome: str) -> MessageDeliveryEvent:
    """Return the neutral event for one possible delivery outcome."""
    recipients = frozenset(
        agent
        for agent, received in zip(AGENTS, outcome)
        if received == "1"
    )
    return MessageDeliveryEvent(
        episode_id=f"possible-{outcome}",
        event_id=f"delivery-{outcome}",
        logical_step=0,
        sequence_index=0,
        sender_id="source",
        message_id="message-1",
        message="signal",
        recipient_ids=recipients,
    )


WEIGHTED_EVENTS = tuple(
    (_delivery_event(outcome), 1 / 8)
    for outcome in OUTCOMES
)


class MessageDeliveryEventTests(unittest.TestCase):
    def test_event_is_immutable(self) -> None:
        event = _delivery_event("011")

        with self.assertRaises(FrozenInstanceError):
            event.sequence_index = 1  # type: ignore[misc]

    def test_invalid_event_fields_are_rejected(self) -> None:
        valid_fields = {
            "episode_id": "episode-1",
            "event_id": "delivery-1",
            "logical_step": 0,
            "sequence_index": 0,
            "sender_id": "source",
            "message_id": "message-1",
            "message": "signal",
            "recipient_ids": frozenset({"A"}),
        }
        invalid_fields = (
            {"episode_id": ""},
            {"event_id": ""},
            {"logical_step": -1},
            {"logical_step": True},
            {"sequence_index": -1},
            {"sequence_index": True},
            {"sender_id": ""},
            {"message_id": ""},
            {"message": ""},
            {"recipient_ids": {"A"}},
            {"recipient_ids": frozenset({""})},
        )

        for replacement in invalid_fields:
            with self.subTest(replacement=replacement):
                fields = valid_fields | replacement
                with self.assertRaises(ValueError):
                    MessageDeliveryEvent(**fields)

    def test_observation_references_truth_without_exposing_state(self) -> None:
        truth = StateTruth(
            episode_id="episode-1",
            event_id="state-1",
            logical_step=0,
            sequence_index=0,
            state="green",
            random_draw=1 / 4,
        )
        observation = ObservationEvent(
            episode_id="episode-1",
            event_id="observation-1",
            logical_step=0,
            sequence_index=1,
            agent_id="A",
            observation="noisy-green",
            channel_id="channel-1",
            source_state_event_id=truth.event_id,
        )

        self.assertEqual(observation.source_state_event_id, truth.event_id)
        self.assertEqual(observation.observation, "noisy-green")
        self.assertFalse(hasattr(observation, "state"))

    def test_logical_time_and_sequence_order_are_distinct(self) -> None:
        first = ObservationEvent(
            episode_id="episode-1",
            event_id="observation-1",
            logical_step=2,
            sequence_index=4,
            agent_id="A",
            observation="green",
            channel_id="channel-1",
            source_state_event_id="state-2",
        )
        second = MessageDeliveryEvent(
            episode_id="episode-1",
            event_id="delivery-1",
            logical_step=2,
            sequence_index=5,
            sender_id="A",
            message_id="message-1",
            message="green",
            recipient_ids=frozenset({"B"}),
        )

        self.assertEqual(first.logical_step, second.logical_step)
        self.assertLess(first.sequence_index, second.sequence_index)

    def test_invalid_truth_and_observation_fields_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            StateTruth(
                episode_id="episode-1",
                event_id="state-1",
                logical_step=0,
                sequence_index=0,
                state="green",
                random_draw=1.0,
            )
        with self.assertRaises(ValueError):
            ObservationEvent(
                episode_id="episode-1",
                event_id="observation-1",
                logical_step=0,
                sequence_index=1,
                agent_id="",
                observation="green",
                channel_id="channel-1",
                source_state_event_id="state-1",
            )

    def test_query_returns_private_scoring_answer(self) -> None:
        event = _delivery_event("011")

        self.assertEqual(recipient_set_query(event), frozenset({"B", "C"}))

    def test_recording_policies_transform_the_same_neutral_events(self) -> None:
        policies = (
            (
                "full",
                lambda event: event.recipient_ids,
                0.0,
                3.0,
            ),
            (
                "local-a",
                lambda event: "A" in event.recipient_ids,
                2.0,
                1.0,
            ),
            (
                "count",
                lambda event: len(event.recipient_ids),
                (6 / 8) * math.log2(3),
                3.0 - (6 / 8) * math.log2(3),
            ),
        )

        for name, policy, remaining, information in policies:
            with self.subTest(policy=name):
                distribution = build_joint_distribution(
                    WEIGHTED_EVENTS,
                    query=recipient_set_query,
                    recording_policy=policy,
                )
                self.assertAlmostEqual(
                    conditional_entropy(distribution.matrix),
                    remaining,
                )
                self.assertAlmostEqual(
                    mutual_information(distribution.matrix),
                    information,
                )


class TransitionEventTests(unittest.TestCase):
    def test_transition_links_state_ids_without_storing_values(self) -> None:
        event = TransitionEvent(
            episode_id="episode-1",
            event_id="transition-1",
            logical_step=1,
            sequence_index=4,
            action_event_id="action-1",
            input_event_ids=("message-1",),
            previous_state_event_id="state-0",
            next_state_event_id="state-1",
        )

        self.assertEqual(event.previous_state_event_id, "state-0")
        self.assertEqual(event.next_state_event_id, "state-1")
        self.assertNotIn("state", event.__dataclass_fields__)

    def test_transition_is_immutable(self) -> None:
        event = TransitionEvent(
            episode_id="episode-1",
            event_id="transition-1",
            logical_step=0,
            sequence_index=0,
            action_event_id="action-1",
            input_event_ids=(),
            previous_state_event_id="state-0",
        )

        with self.assertRaises(FrozenInstanceError):
            event.action_event_id = "action-2"  # type: ignore[misc]

    def test_missing_next_state_is_allowed(self) -> None:
        event = TransitionEvent(
            episode_id="episode-1",
            event_id="transition-1",
            logical_step=0,
            sequence_index=0,
            action_event_id="action-1",
            input_event_ids=(),
            previous_state_event_id="state-0",
        )

        self.assertIsNone(event.next_state_event_id)

    def test_invalid_transition_fields_are_rejected(self) -> None:
        valid_fields = {
            "episode_id": "episode-1",
            "event_id": "transition-1",
            "logical_step": 0,
            "sequence_index": 0,
            "action_event_id": "action-1",
            "input_event_ids": ("message-1",),
            "previous_state_event_id": "state-0",
            "next_state_event_id": "state-1",
        }
        invalid_fields = (
            {"action_event_id": ""},
            {"input_event_ids": ("message-1", "message-1")},
            {"input_event_ids": ("",)},
            {"previous_state_event_id": ""},
            {"next_state_event_id": ""},
        )

        for replacement in invalid_fields:
            with self.subTest(replacement=replacement):
                fields = valid_fields | replacement
                with self.assertRaises(ValueError):
                    TransitionEvent(**fields)


if __name__ == "__main__":
    unittest.main(verbosity=2)
