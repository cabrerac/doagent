"""Tests for traceability records."""

import unittest

from doagent.core import InMemorySharedData, new_record, new_trace_record


class TestTraceabilityRecords(unittest.TestCase):
    def setUp(self) -> None:
        self.shared_data = InMemorySharedData()

    def test_trace_links_records(self) -> None:
        """Ensure trace records link upstream and downstream records."""
        upstream = new_record(
            actor="agent-1",
            kind="note",
            payload={"text": "source"},
        )
        downstream = new_record(
            actor="agent-2",
            kind="decision",
            payload={"decision": {"action": "use"}},
        )
        self.shared_data.write(upstream)
        self.shared_data.write(downstream)

        trace = new_trace_record(
            actor="agent-2",
            from_id=upstream.id,
            to_id=downstream.id,
            relation="used",
            notes="Decision used upstream note.",
        )
        self.shared_data.write(trace)

        traces = list(self.shared_data.listen("trace"))
        self.assertEqual(len(traces), 1)
        payload = traces[0].payload
        self.assertEqual(payload["from_id"], upstream.id)
        self.assertEqual(payload["to_id"], downstream.id)
        self.assertEqual(payload["relation"], "used")
        self.assertEqual(payload["notes"], "Decision used upstream note.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
