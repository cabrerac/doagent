"""Test Hidden Profile played through a DOAgent session."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiments.information_flow.hidden_profile.cost import median, repeated_cost
from experiments.information_flow.hidden_profile.rules import run_episode
from experiments.information_flow.hidden_profile.run_doagent import (
    comparable_session,
    run_session,
)


class HiddenProfileDoagentTests(unittest.TestCase):
    """Check that a session plays the same episode as the rules alone."""

    def test_session_events_match_the_rules(self) -> None:
        """Replay one seed through the session and through the rules."""
        with tempfile.TemporaryDirectory() as folder:
            result = run_session(17, logging_level=1, output_base=folder)
        self.assertEqual(result.rules.episode(), run_episode(17))

    def test_each_logging_level_keeps_the_events(self) -> None:
        """Run levels 0, 1, and 2 without changing the episode."""
        direct = run_episode(4)
        for level in (0, 1, 2):
            with tempfile.TemporaryDirectory() as folder:
                result = run_session(4, logging_level=level, output_base=folder)
            self.assertEqual(result.rules.episode(), direct)

    def test_records_hold_outcomes_decisions_and_traces(self) -> None:
        """Export the session record kinds for one episode."""
        with tempfile.TemporaryDirectory() as folder:
            result = run_session(3, logging_level=1, output_base=folder)
            records = json.loads(result.records_path.read_text(encoding="utf-8"))
            self.assertTrue(result.records_path.is_file())
            self.assertFalse((Path(folder) / "scoring_sink.json").exists())
        self.assertEqual(set(records), {"agent_update", "observation", "outcome", "trace"})
        self.assertGreater(len(records["outcome"]), 0)
        self.assertGreater(len(records["agent_update"]), 0)
        self.assertGreater(len(records["trace"]), 0)
        self.assertNotIn("env_update", records)

    def test_a_repeated_session_matches_without_the_library_id_or_clock(self) -> None:
        """Replay each logging level and compare the records aside from id and clock."""
        for level in (0, 1, 2):
            with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
                left = run_session(17, logging_level=level, output_base=first)
                right = run_session(17, logging_level=level, output_base=second)
                left_bytes = left.records_path.read_bytes()
                right_bytes = right.records_path.read_bytes()
                left_text = json.loads(left_bytes)
                right_text = json.loads(right_bytes)
            self.assertEqual(comparable_session(left_text), comparable_session(right_text))
            if level == 1:
                self.assertNotEqual(left_bytes, right_bytes)

    def test_a_scripted_run_reports_no_tokens(self) -> None:
        """Count tokens as zero and accept a non-negative time."""
        self.assertEqual(median((1.0, 3.0, 2.0)), 2.0)

        def play() -> None:
            with tempfile.TemporaryDirectory() as folder:
                run_session(1, logging_level=0, output_base=folder)

        cost = repeated_cost("D0", play, repeats=1)
        self.assertEqual(cost.tokens, 0)
        self.assertGreaterEqual(cost.seconds, 0.0)

    def test_store_links_follow_the_logging_level(self) -> None:
        """Level 1 and 2 name the records that were shown. Level 0 does not."""
        from experiments.information_flow.hidden_profile.rules import run_episode

        for seed in range(18):
            direct = run_episode(seed)
            for level in (0, 1, 2):
                with tempfile.TemporaryDirectory() as folder:
                    result = run_session(seed, logging_level=level, output_base=folder)
                    records = json.loads(result.records_path.read_text(encoding="utf-8"))
                self.assertEqual(result.rules.episode(), direct)
                decisions = records["agent_update"]
                self.assertGreater(len(decisions), 0)
                if level == 0:
                    self.assertTrue(all(not decision["provenance"] for decision in decisions))
                else:
                    self.assertTrue(all(
                        decision["provenance"].get("derived_from") for decision in decisions
                    ))

    def test_withholding_the_observation_stops_the_scripted_choice(self) -> None:
        """Removing the shown observation record stops the scripted disclosure."""
        from doagent.core import (
            InMemorySharedData,
            PolicyRegistry,
            RunConfig,
            Session,
            Topology,
            TopologyConfig,
        )
        from experiments.information_flow.hidden_profile.policies import scripted_policy
        from experiments.information_flow.hidden_profile.rules import HiddenProfileRules

        rules = HiddenProfileRules()
        session = Session(
            InMemorySharedData(),
            RunConfig(logging_level=1),
            topology=TopologyConfig(mode=Topology.PEER_TO_PEER),
            visibility={
                agent_id: ["hidden_profile_env"] for agent_id in rules.agents
            },
        )
        registry = PolicyRegistry()
        for agent_id in rules.agents:
            policy = scripted_policy(agent_id)

            def factory(params, policy=policy):
                del params
                return policy

            registry.register(agent_id, factory)
        env = session.wrap_env(rules, env_actor="hidden_profile_env")
        agents = session.create_agents(
            [
                {"id": agent_id, "policy": {"name": agent_id, "params": {}}}
                for agent_id in rules.agents
            ],
            registry,
        )
        env.reset(seed=0)
        agent_id = rules.agents[0]
        agents[agent_id].decide(round_id=1)
        decision = [
            record for record in session.inspect("agent_update") if record.actor == agent_id
        ][-1]
        observation_ids = [
            record_id
            for record_id in decision.provenance["derived_from"]
            if session.shared_data.read(record_id).kind == "observation"
        ]
        self.assertTrue(observation_ids)
        with self.assertRaises(ValueError):
            session.repeat_decision(
                agents[agent_id],
                decision.id,
                withhold=observation_ids,
                times=1,
            )
        stored = session.inspect("decision_repeat")
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].payload["variant"], "original")
        self.assertEqual(stored[0].provenance["derived_from"], [decision.id])


if __name__ == "__main__":
    unittest.main()
