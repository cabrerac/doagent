"""Tests for interpretability (explanation inside decision)."""

import unittest

from doagent.core import InMemorySharedData, new_agent_update_record


class TestInterpretabilityRecords(unittest.TestCase):
    def setUp(self) -> None:
        self.shared_data = InMemorySharedData()

    def test_explanation_in_decision(self) -> None:
        """Ensure explanation is stored inside agent_update decision."""
        agent_update = new_agent_update_record(
            actor="agent-1",
            local_knowledge={},
            decision={
                "request": {},
                "response": {"choice": {"status": "act", "action": "approve"}},
                "explanation": "Approved due to policy compliance.",
                "evidence": ["policy-1"],
            },
        )
        self.shared_data.write(agent_update)

        updates = list(self.shared_data.listen("agent_update"))
        self.assertEqual(len(updates), 1)
        decision = updates[0].payload["decision"]
        self.assertEqual(decision["explanation"], "Approved due to policy compliance.")
        self.assertEqual(decision["evidence"], ["policy-1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
