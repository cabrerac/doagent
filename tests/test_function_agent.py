"""Tests for the function-backed agent adapter."""

import unittest

from doagent.core import FunctionAgent, InMemorySharedData


class TestFunctionAgent(unittest.TestCase):
    def setUp(self) -> None:
        self.shared_data = InMemorySharedData()

    def test_decide_persists_decision_record(self) -> None:
        """Ensure decisions are persisted to shared data."""
        def decide_fn(request: dict) -> dict:
            return {"decision": {"action": "approve"}, "notes": "ok"}

        agent = FunctionAgent("agent-1", self.shared_data, decide_fn)
        response = agent.decide(
            {
                "id": "req-1",
                "actor": "agent-1",
                "goal": "approve request",
                "context": {"priority": "high"},
            }
        )

        self.assertEqual(response["request_id"], "req-1")
        self.assertEqual(response["actor"], "agent-1")
        self.assertIn("id", response)

        records = list(self.shared_data.listen("decision"))
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.payload["request"]["id"], "req-1")
        self.assertEqual(record.payload["response"]["id"], response["id"])
        self.assertEqual(record.payload["response"]["decision"]["action"], "approve")


if __name__ == "__main__":
    unittest.main(verbosity=2)
