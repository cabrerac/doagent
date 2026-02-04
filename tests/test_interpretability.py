"""Tests for interpretability explanation records."""

import unittest

from doagent.core import InMemorySharedData, new_explanation_record, new_record


class TestInterpretabilityRecords(unittest.TestCase):
    def setUp(self) -> None:
        self.shared_data = InMemorySharedData()

    def test_explanation_links_to_decision(self) -> None:
        """Ensure explanation records reference decision ids."""
        decision = new_record(
            actor="agent-1",
            kind="decision",
            payload={"decision": {"action": "approve"}},
        )
        self.shared_data.write(decision)

        explanation = new_explanation_record(
            actor="agent-1",
            decision_id=decision.id,
            summary="Approved due to policy compliance.",
            evidence=["policy-1"],
        )
        self.shared_data.write(explanation)

        explanations = list(self.shared_data.listen("explanation"))
        self.assertEqual(len(explanations), 1)
        payload = explanations[0].payload
        self.assertEqual(payload["decision_id"], decision.id)
        self.assertEqual(payload["summary"], "Approved due to policy compliance.")
        self.assertEqual(payload["evidence"], ["policy-1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
