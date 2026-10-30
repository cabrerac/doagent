"""Test the frozen Hidden Profile question list on seed 0."""

from __future__ import annotations

import unittest

from experiments.information_flow.hidden_profile.rules import run_episode
from experiments.information_flow.queries import QUERIES, Answer, decode

QUERY_IDS = (
    "sender",
    "recipients",
    "fact_access",
    "decision_action",
    "group_votes",
    "event_order",
    "first_access",
    "decision_observation",
    "decision_inputs",
    "fact_path",
    "transition_update",
    "reported_chances",
    "vote_basis",
    "belief_change",
    "vote_matches_chances",
)


class QueryContractTests(unittest.TestCase):
    """Lock the question deck and the seed 0 answers."""

    def test_question_list_is_the_deck(self) -> None:
        """Keep the question identifiers in deck order."""
        self.assertEqual(tuple(query.id for query in QUERIES), QUERY_IDS)

    def test_seed_0_answers_match_the_deal(self) -> None:
        """Read seed 0 from its events and check the known deal."""
        events = run_episode(0).events
        recipients = decode(events, "recipients", event_id="disclosure-1-agent-c")
        early = decode(events, "fact_access", fact_id="f6", logical_step=0)
        later = decode(events, "fact_access", fact_id="f6", logical_step=1)
        first_holder = decode(events, "first_access", fact_id="f6", agent_id="agent-c")
        first_recipient = decode(
            events,
            "first_access",
            fact_id="f6",
            agent_id="agent-a",
        )
        never = decode(events, "first_access", fact_id="f6", agent_id="agent-b")
        observation = decode(events, "decision_observation", event_id="vote-agent-c")
        inputs = decode(events, "decision_inputs", event_id="vote-agent-a")
        transition = decode(events, "transition_update", event_id="outcome-group")
        order = decode(
            events,
            "event_order",
            event_ids=("disclosure-1-agent-c", "disclosure-0-agent-c"),
        )
        self.assertEqual(recipients, Answer("exact", frozenset({"agent-a"})))
        self.assertEqual(early, Answer("exact", frozenset({"agent-c"})))
        self.assertEqual(later, Answer("exact", frozenset({"agent-a", "agent-c"})))
        self.assertEqual(first_holder, Answer("exact", "deal-agent-c"))
        self.assertEqual(first_recipient, Answer("exact", "disclosure-1-agent-c"))
        self.assertEqual(never, Answer("unknown"))
        self.assertEqual(observation, Answer("exact", "f1,f2,f3,f6"))
        self.assertEqual(inputs, Answer("exact", ("belief-2-agent-a",)))
        self.assertEqual(transition, Answer("unknown"))
        self.assertEqual(
            order,
            Answer("exact", ("disclosure-0-agent-c", "disclosure-1-agent-c")),
        )
        sender = decode(events, "sender", event_id="disclosure-1-agent-c")
        group_votes = decode(events, "group_votes", event_id="outcome-group")
        path = decode(events, "fact_path", fact_id="f6", agent_id="agent-a")
        holder_path = decode(events, "fact_path", fact_id="f6", agent_id="agent-c")
        chances = decode(events, "reported_chances", event_id="belief-2-agent-a")
        after_message = decode(events, "reported_chances", event_id="belief-1-agent-a")
        change = decode(
            events,
            "belief_change",
            event_id="disclosure-1-agent-c",
            agent_id="agent-a",
        )
        basis = decode(events, "vote_basis", event_id="vote-agent-a")
        self.assertEqual(sender, Answer("exact", "agent-c"))
        self.assertEqual(
            group_votes,
            Answer("exact", ("vote-agent-a", "vote-agent-b", "vote-agent-c")),
        )
        self.assertEqual(holder_path, Answer("exact", ("deal-agent-c",)))
        self.assertEqual(
            path,
            Answer("exact", ("deal-agent-c", "disclosure-1-agent-c")),
        )
        self.assertEqual(chances.kind, "exact")
        self.assertEqual(change.kind, "exact")
        assert isinstance(change.value, tuple)
        self.assertEqual(change.value[1], after_message.value)
        self.assertEqual(basis.kind, "exact")
        assert isinstance(basis.value, tuple)
        self.assertEqual(basis.value[0], chances.value)
        for agent_id in ("agent-a", "agent-b", "agent-c"):
            action = decode(events, "decision_action", event_id=f"vote-{agent_id}")
            matched = decode(events, "vote_matches_chances", event_id=f"vote-{agent_id}")
            self.assertEqual(action, Answer("exact", (agent_id, "route-hill")))
            self.assertEqual(matched, Answer("exact", True))

    def test_answer_kinds_stay_separate(self) -> None:
        """Reject an answer that mixes a value with candidates."""
        with self.assertRaises(ValueError):
            Answer("exact", None)
        with self.assertRaises(ValueError):
            Answer("candidates", candidates=("only-one",))


if __name__ == "__main__":
    unittest.main()
