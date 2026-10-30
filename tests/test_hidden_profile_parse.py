"""Test parsers that rebuild Hidden Profile events from artifacts."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiments.information_flow.hidden_profile.access import analyst_logs
from experiments.information_flow.hidden_profile.parse import (
    parse_doagent,
    parse_marble,
    vote_bases,
)
from experiments.information_flow.hidden_profile.service_trace import (
    LINE_FIELDS,
    parse_service_trace,
)
from experiments.information_flow.hidden_profile.rules import run_episode
from experiments.information_flow.hidden_profile.run_doagent import run_session
from experiments.information_flow.hidden_profile.run_marble import run_marble
from experiments.information_flow.queries import Answer, decode


class HiddenProfileParseTests(unittest.TestCase):
    """Check seed 0 answers recovered from both artifact kinds."""

    def test_both_artifacts_answer_seed_0(self) -> None:
        """Recover the f6 path and the hill votes from each artifact."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session = run_session(0, logging_level=1, output_base=root / "doagent")
            run_marble(0, root / "marble")
            parsed = (
                parse_doagent(session.records_path),
                parse_marble(root / "marble" / "logs"),
            )
            self.assertFalse((root / "doagent" / "scoring_sink.json").exists())
            self.assertFalse((root / "marble" / "scoring_sink.json").exists())
        for events in parsed:
            recipients = decode(events, "recipients", event_id="disclosure-1-agent-c")
            early = decode(events, "fact_access", fact_id="f6", logical_step=0)
            later = decode(events, "fact_access", fact_id="f6", logical_step=1)
            transition = decode(events, "transition_update", event_id="outcome-group")
            self.assertEqual(recipients, Answer("exact", frozenset({"agent-a"})))
            self.assertEqual(early, Answer("exact", frozenset({"agent-c"})))
            self.assertEqual(later, Answer("exact", frozenset({"agent-a", "agent-c"})))
            self.assertEqual(transition, Answer("unknown"))
            for agent_id in ("agent-a", "agent-b", "agent-c"):
                action = decode(events, "decision_action", event_id=f"vote-{agent_id}")
                self.assertEqual(action, Answer("exact", (agent_id, "route-hill")))

    def test_session_links_name_the_votes_and_the_chance_change(self) -> None:
        """Read the vote links and the stored chances, and leave gaps when they are absent."""
        rules = run_episode(0).events
        message = "disclosure-1-agent-c"
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session = run_session(0, logging_level=1, output_base=root / "doagent")
            records_path = session.records_path
            document = json.loads(records_path.read_text(encoding="utf-8"))
            events = parse_doagent(records_path)
            stripped_votes = root / "no-traces.json"
            stripped_chances = root / "no-chances.json"
            without_traces = dict(document)
            without_traces["trace"] = []
            stripped_votes.write_text(json.dumps(without_traces), encoding="utf-8")
            without_chances = json.loads(json.dumps(document))
            for record in without_chances["outcome"]:
                observations = record["payload"]["observations"]
                for observation in observations.values():
                    observation.pop("belief", None)
            stripped_chances.write_text(json.dumps(without_chances), encoding="utf-8")
            missing_votes = parse_doagent(stripped_votes)
            missing_chances = parse_doagent(stripped_chances)
            run_marble(0, root / "marble")
            log_events = parse_marble(root / "marble" / "logs")
        self.assertEqual(
            decode(events, "group_votes", event_id="outcome-group"),
            decode(rules, "group_votes", event_id="outcome-group"),
        )
        self.assertEqual(
            decode(events, "belief_change", event_id=message, agent_id="agent-a"),
            decode(rules, "belief_change", event_id=message, agent_id="agent-a"),
        )
        self.assertEqual(
            decode(events, "transition_update", event_id="outcome-group"),
            Answer("unknown"),
        )
        self.assertEqual(
            decode(missing_votes, "group_votes", event_id="outcome-group"),
            Answer("unknown"),
        )
        self.assertEqual(
            decode(missing_votes, "belief_change", event_id=message, agent_id="agent-a"),
            decode(rules, "belief_change", event_id=message, agent_id="agent-a"),
        )
        self.assertEqual(
            decode(missing_chances, "belief_change", event_id=message, agent_id="agent-a"),
            Answer("unknown"),
        )
        self.assertEqual(
            decode(missing_chances, "group_votes", event_id="outcome-group"),
            decode(rules, "group_votes", event_id="outcome-group"),
        )
        self.assertEqual(
            decode(log_events, "group_votes", event_id="outcome-group"),
            Answer("unknown"),
        )
        self.assertEqual(
            decode(log_events, "belief_change", event_id=message, agent_id="agent-a"),
            Answer("unknown"),
        )

    def test_vote_basis_is_stated_only_on_the_session(self) -> None:
        """Read the chances and the fact names behind each vote."""
        agents = ("agent-a", "agent-b", "agent-c")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session = run_session(0, logging_level=1, output_base=root / "doagent")
            run_marble(0, root / "marble")
            session_events = parse_doagent(session.records_path)
            log_events = parse_marble(root / "marble" / "logs")
        rules = vote_bases(run_episode(0).events, agents)
        found = vote_bases(session_events, agents)
        missing = vote_bases(log_events, agents)
        self.assertEqual(found, rules)
        self.assertTrue(all(answer.kind == "exact" for answer in rules))
        agent_a = found[0]
        self.assertIsNotNone(agent_a.value)
        assert isinstance(agent_a.value, tuple)
        self.assertEqual(agent_a.value[1], ("f1", "f2", "f3", "f4", "f6"))
        self.assertEqual(missing, tuple(Answer("unknown") for _ in agents))

    def test_a_vote_line_states_a_basis_only_when_it_includes_one(self) -> None:
        """Read chances and fact names from a vote line that states them."""
        stated = (
            "Chose an action. kind=vote option=route-hill "
            "options=route-hill,route-tunnel,route-bridge "
            "belief=0.5,0.25,0.25 facts=f1,f4\n"
        )
        plain = "Chose an action. kind=vote option=route-hill\n"
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stated_path = root / "HiddenProfileAgent.agent-a.log"
            plain_path = root / "HiddenProfileAgent.agent-b.log"
            stated_path.write_text(stated, encoding="utf-8")
            plain_path.write_text(plain, encoding="utf-8")
            stated_events = parse_marble(root, [stated_path])
            plain_events = parse_marble(root, [plain_path])
        stated_basis = vote_bases(stated_events, ("agent-a",))[0]
        plain_basis = vote_bases(plain_events, ("agent-b",))[0]
        self.assertEqual(
            stated_basis,
            Answer(
                "exact",
                (
                    (
                        ("route-hill", 0.5),
                        ("route-tunnel", 0.25),
                        ("route-bridge", 0.25),
                    ),
                    ("f1", "f4"),
                ),
            ),
        )
        self.assertEqual(plain_basis, Answer("unknown"))

    def test_partial_logs_leave_gaps_for_seed_0(self) -> None:
        """Ask seed 0 of one log, the three agent logs, and every log."""
        with tempfile.TemporaryDirectory() as folder:
            log_dir = Path(folder) / "logs"
            run_marble(0, folder)
            every = parse_marble(log_dir, analyst_logs(log_dir, "Sall"))
            agents = parse_marble(
                log_dir,
                analyst_logs(
                    log_dir,
                    "Sk",
                    (
                        "HiddenProfileAgent.agent-a.log",
                        "HiddenProfileAgent.agent-b.log",
                        "HiddenProfileAgent.agent-c.log",
                    ),
                ),
            )
            holder = parse_marble(
                log_dir,
                analyst_logs(log_dir, "S1", "HiddenProfileAgent.agent-c.log"),
            )
            other = parse_marble(
                log_dir,
                analyst_logs(log_dir, "S1", "HiddenProfileAgent.agent-b.log"),
            )
        self.assertEqual(
            decode(every, "recipients", event_id="disclosure-1-agent-c"),
            Answer("exact", frozenset({"agent-a"})),
        )
        self.assertEqual(
            decode(every, "fact_access", fact_id="f6", logical_step=0),
            Answer("exact", frozenset({"agent-c"})),
        )
        self.assertEqual(
            decode(agents, "recipients", event_id="disclosure-1-agent-c"),
            Answer("exact", frozenset({"agent-a"})),
        )
        self.assertEqual(
            decode(agents, "fact_access", fact_id="f6", logical_step=0),
            Answer("unknown"),
        )
        self.assertEqual(
            decode(agents, "fact_access", fact_id="f6", logical_step=1),
            Answer("unknown"),
        )
        self.assertEqual(
            decode(holder, "recipients", event_id="disclosure-1-agent-c"),
            Answer("exact", frozenset({"agent-a"})),
        )
        self.assertEqual(
            decode(holder, "fact_access", fact_id="f6", logical_step=1),
            Answer("unknown"),
        )
        self.assertEqual(
            decode(holder, "decision_action", event_id="vote-agent-c"),
            Answer("exact", ("agent-c", "route-hill")),
        )
        self.assertEqual(
            decode(holder, "decision_action", event_id="vote-agent-a"),
            Answer("unknown"),
        )
        self.assertEqual(
            decode(other, "recipients", event_id="disclosure-1-agent-c"),
            Answer("unknown"),
        )
        self.assertEqual(
            decode(other, "decision_action", event_id="vote-agent-b"),
            Answer("exact", ("agent-b", "route-hill")),
        )

    def test_a_structured_vote_states_a_basis_only_when_it_includes_one(self) -> None:
        """Read chances and fact names from a structured vote that states them."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "service_trace.jsonl"
            lines = [
                _trace_line("deal", "HiddenProfileEnv", {"agent-a": ["f1"]}, "deal"),
                _trace_line(
                    "vote",
                    "HiddenProfileAgent.agent-a",
                    {
                        "kind": "vote",
                        "option": "route-hill",
                        "options": ["route-hill", "route-tunnel", "route-bridge"],
                        "belief": [0.5, 0.25, 0.25],
                        "facts": ["f4", "f1"],
                    },
                    "vote-agent-a",
                ),
            ]
            path.write_text(
                "".join(json.dumps(line, sort_keys=True) + "\n" for line in lines),
                encoding="utf-8",
            )
            events = parse_service_trace(path)
        basis = vote_bases(events, ("agent-a",))[0]
        self.assertEqual(
            basis,
            Answer(
                "exact",
                (
                    (
                        ("route-hill", 0.5),
                        ("route-tunnel", 0.25),
                        ("route-bridge", 0.25),
                    ),
                    ("f1", "f4"),
                ),
            ),
        )


def _trace_line(
    operation: str,
    service: str,
    payload: dict[str, object],
    message_id: str,
) -> dict[str, object]:
    """Return one structured trace line with the fields the reader expects."""
    record = {
        "callee": service,
        "caller": "HiddenProfileEngine",
        "message_id": message_id,
        "operation": operation,
        "parent_id": "engine-run",
        "payload": payload,
        "service": service,
        "status": "ok",
        "timestamp": "2026-10-29T00:00:00Z",
    }
    if tuple(sorted(record)) != LINE_FIELDS:
        raise ValueError("the test trace line is missing a field")
    return record


if __name__ == "__main__":
    unittest.main()
