"""Verify the controlled information-flow environment end to end."""

import unittest

from experiments.information_flow.environment import (
    DEFAULT_CONFIG,
    EnvironmentConfig,
    ObservationChannel,
    SignallingRules,
    run_episode,
)
from experiments.information_flow.policies import signalling_policy
from experiments.information_flow.events import (
    ActionEvent,
    BeliefEvent,
    MessageDeliveryEvent,
    ObservationEvent,
    OutcomeEvent,
    StateTruth,
)


class ControlledEnvironmentTests(unittest.TestCase):
    def test_episode_contains_private_truth_and_complete_visible_path(self) -> None:
        episode = run_episode(17)

        self.assertIsInstance(episode.truth, StateTruth)
        self.assertEqual(len(episode.events), 13)
        self.assertEqual(
            [event.sequence_index for event in episode.events],
            list(range(1, 14)),
        )
        self.assertTrue(all(event.logical_step == 0 for event in episode.events))
        self.assertFalse(any(isinstance(event, StateTruth) for event in episode.events))
        self.assertEqual(
            sum(isinstance(event, ObservationEvent) for event in episode.events),
            3,
        )
        self.assertEqual(
            sum(isinstance(event, MessageDeliveryEvent) for event in episode.events),
            1,
        )
        self.assertEqual(
            sum(isinstance(event, BeliefEvent) for event in episode.events),
            3,
        )
        self.assertEqual(
            sum(isinstance(event, ActionEvent) for event in episode.events),
            3,
        )
        self.assertEqual(
            sum(isinstance(event, OutcomeEvent) for event in episode.events),
            3,
        )

    def test_identical_seed_reproduces_truth_and_events(self) -> None:
        first = run_episode(29)
        second = run_episode(29)

        self.assertEqual(first, second)

    def test_perfect_channels_produce_correct_beliefs_actions_and_outcomes(self) -> None:
        config = EnvironmentConfig(
            states=("amber", "blue", "green", "red"),
            observation_channels=(
                ObservationChannel("agent-a", 1.0),
                ObservationChannel("agent-b", 1.0),
                ObservationChannel("agent-c", 1.0),
            ),
            sender_id="agent-a",
            recipient_ids=("agent-b", "agent-c"),
            delivery_probability=1.0,
        )
        episode = run_episode(3, config)

        message = next(
            event
            for event in episode.events
            if isinstance(event, MessageDeliveryEvent)
        )
        beliefs = [
            event
            for event in episode.events
            if isinstance(event, BeliefEvent)
        ]
        actions = [
            event
            for event in episode.events
            if isinstance(event, ActionEvent)
        ]
        outcomes = [
            event
            for event in episode.events
            if isinstance(event, OutcomeEvent)
        ]

        self.assertEqual(message.recipient_ids, frozenset({"agent-b", "agent-c"}))
        self.assertEqual(message.message, episode.truth.state)
        for belief in beliefs:
            state_probability = dict(
                zip(belief.state_labels, belief.probabilities)
            )
            self.assertEqual(state_probability[episode.truth.state], 1.0)
        self.assertTrue(
            all(action.action == episode.truth.state for action in actions)
        )
        self.assertTrue(
            all(outcome.outcome == "correct" for outcome in outcomes)
        )

    def test_single_observation_beliefs_match_symmetric_channels(self) -> None:
        config = EnvironmentConfig(
            states=DEFAULT_CONFIG.states,
            observation_channels=DEFAULT_CONFIG.observation_channels,
            sender_id=DEFAULT_CONFIG.sender_id,
            recipient_ids=DEFAULT_CONFIG.recipient_ids,
            delivery_probability=0.0,
        )
        episode = run_episode(41, config)
        observations = {
            event.agent_id: event
            for event in episode.events
            if isinstance(event, ObservationEvent)
        }
        beliefs = {
            event.agent_id: event
            for event in episode.events
            if isinstance(event, BeliefEvent)
        }

        for channel in config.observation_channels:
            observation = observations[channel.agent_id].observation
            belief = beliefs[channel.agent_id]
            probability_by_state = dict(
                zip(belief.state_labels, belief.probabilities)
            )
            self.assertAlmostEqual(
                probability_by_state[observation],
                channel.accuracy,
            )
            self.assertNotIn("message-0", belief.input_event_ids)

    def test_message_is_an_input_only_for_actual_recipients(self) -> None:
        episode = run_episode(53)
        message = next(
            event
            for event in episode.events
            if isinstance(event, MessageDeliveryEvent)
        )
        beliefs = [
            event
            for event in episode.events
            if isinstance(event, BeliefEvent)
        ]

        for belief in beliefs:
            has_message_input = message.event_id in belief.input_event_ids
            self.assertEqual(
                has_message_input,
                belief.agent_id in message.recipient_ids,
            )

    def test_outcomes_reference_the_actions_they_score(self) -> None:
        episode = run_episode(61)
        actions = {
            event.event_id: event
            for event in episode.events
            if isinstance(event, ActionEvent)
        }
        outcomes = [
            event
            for event in episode.events
            if isinstance(event, OutcomeEvent)
        ]

        for outcome in outcomes:
            action = actions[outcome.action_event_id]
            expected = (
                "correct"
                if action.action == episode.truth.state
                else "incorrect"
            )
            self.assertEqual(outcome.agent_id, action.agent_id)
            self.assertEqual(outcome.outcome, expected)

    def test_reset_and_step_replay_the_scripted_episode(self) -> None:
        rules = SignallingRules()
        observations = rules.reset(seed=17)
        self.assertEqual(
            set(observations),
            {"agent-a", "agent-b", "agent-c"},
        )
        for observation in observations.values():
            self.assertEqual(observation["phase"], "send")
            self.assertNotIn("state", observation)
        policies = {
            agent_id: signalling_policy(agent_id, DEFAULT_CONFIG)
            for agent_id in observations
        }
        delivered = rules.step(
            {
                "agent-a": policies["agent-a"](observations["agent-a"]),
            }
        )
        self.assertEqual(
            set(delivered),
            {"observations", "rewards", "done"},
        )
        self.assertTrue(all(done is False for done in delivered["done"].values()))
        for observation in delivered["observations"].values():
            self.assertNotIn("state", observation)
        finished = rules.step(
            {
                agent_id: policies[agent_id](observation)
                for agent_id, observation in delivered["observations"].items()
            }
        )
        self.assertTrue(all(finished["done"].values()))
        self.assertTrue(
            all(reward in (0.0, 1.0) for reward in finished["rewards"].values())
        )
        self.assertEqual(rules.episode(), run_episode(17))


if __name__ == "__main__":
    unittest.main(verbosity=2)
