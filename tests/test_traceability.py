"""Tests for traceability records."""

import unittest

from doagent.core import (
    InMemorySharedData,
    new_agent_update_record,
    new_record,
    new_trace_record,
)


class TestTraceabilityRecords(unittest.TestCase):
    def setUp(self) -> None:
        self.shared_data = InMemorySharedData()

    def test_trace_links_outcomes_via_agent_update(self) -> None:
        """Ensure trace records link outcomes with enabled_by agent_update."""
        from_outcome = new_record(
            actor="env",
            kind="outcome",
            payload={"round": 0},
        )
        agent_update = new_agent_update_record(
            actor="agent-1",
            local_knowledge={},
            decision={"request": {}, "response": {"decision": {}}},
        )
        to_outcome = new_record(
            actor="env",
            kind="outcome",
            payload={"round": 1},
        )
        self.shared_data.write(from_outcome)
        self.shared_data.write(agent_update)
        self.shared_data.write(to_outcome)

        trace = new_trace_record(
            actor="agent-1",
            from_id=from_outcome.id,
            to_id=to_outcome.id,
            enabled_by_id=agent_update.id,
            relation="enables",
            round_=1,
            notes="Transition enabled by agent.",
        )
        self.shared_data.write(trace)

        traces = list(self.shared_data.listen("trace"))
        self.assertEqual(len(traces), 1)
        payload = traces[0].payload
        self.assertEqual(payload["from_id"], from_outcome.id)
        self.assertEqual(payload["to_id"], to_outcome.id)
        self.assertEqual(payload["enabled_by_id"], agent_update.id)
        self.assertEqual(payload["relation"], "enables")
        self.assertEqual(payload["notes"], "Transition enabled by agent.")
