"""Tests for on-demand decision step views."""

import unittest

from doagent.analysis.views import decision_steps


def _update(
    step: int,
    agent: str,
    output: dict,
    *,
    record_id: str,
    explanation: str | None = None,
):
    """Build one agent_update record for view tests.

    Args:
        step:
            Decision round.
        agent:
            Agent id.
        output:
            Action placed on the decision response.
        record_id:
            Record id.
        explanation:
            Optional explanation stored on the decision.

    Returns:
        A native-looking agent_update dict.
    """
    decision = {
        "request": {"context": {"round": step}, "inputs": {"seen": agent}},
        "response": {"choice": {"action": output, "status": "act"}},
    }
    if explanation:
        decision["explanation"] = explanation
    return {
        "id": record_id,
        "actor": agent,
        "kind": "agent_update",
        "payload": {"decision": decision},
        "provenance": {},
    }


class TestDecisionSteps(unittest.TestCase):
    def test_level_zero_keeps_step_fields_only(self):
        records = [
            {
                "id": "join",
                "actor": "solver",
                "kind": "participation",
                "payload": {"event": "join"},
            },
            _update(1, "solver", {"type": "solve", "value": 8}, record_id="u1"),
            {
                "id": "out1",
                "actor": "env",
                "kind": "outcome",
                "payload": {"round": 1, "actions": {"solver": {"value": 8}}},
            },
        ]
        steps = decision_steps(records, level=0)
        self.assertEqual(len(steps), 1)
        self.assertEqual(
            steps[0],
            {
                "step": 1,
                "agent": "solver",
                "input": {"seen": "solver"},
                "output": {"type": "solve", "value": 8},
            },
        )

    def test_level_one_adds_readable_links(self):
        records = [
            _update(0, "orchestrator", {"type": "assign"}, record_id="u0"),
            {
                "id": "out0",
                "actor": "env",
                "kind": "outcome",
                "payload": {"round": 0},
            },
            _update(1, "solver", {"value": 8}, record_id="u1"),
            {
                "id": "out1",
                "actor": "env",
                "kind": "outcome",
                "payload": {"round": 1},
            },
            {
                "id": "t1",
                "actor": "solver",
                "kind": "trace",
                "payload": {
                    "from_id": "out0",
                    "to_id": "out1",
                    "enabled_by_id": "u1",
                    "relation": "enables",
                },
            },
        ]
        steps = decision_steps(records, level=1)
        self.assertEqual(steps[1]["agent"], "solver")
        self.assertEqual(
            steps[1]["links"],
            [{"relation": "enables", "from": "outcome@0", "to": "outcome@1"}],
        )
        self.assertNotIn("explanation", steps[1])

    def test_level_two_adds_explanation(self):
        records = [
            _update(
                2,
                "checker",
                {"accept": True},
                record_id="u2",
                explanation="Accept 8.",
            )
        ]
        steps = decision_steps(records, level=2)
        self.assertEqual(steps[0]["explanation"], "Accept 8.")

    def test_unknown_level_is_rejected(self):
        with self.assertRaises(ValueError):
            decision_steps([], level=3)
