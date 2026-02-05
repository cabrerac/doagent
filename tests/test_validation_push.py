"""Tests for simple push validation scenario."""

import tempfile
import unittest
from pathlib import Path

from doagent.core import FileSharedData, InMemorySharedData
from doagent.records import new_provenance
from doagent.validation import (
    NoOpSharedData,
    PolicyRegistry,
    PushAgentConfig,
    make_push_env,
    measure_baseline,
    output_bytes_from_path,
    run_push_validation,
)


def _register_policies(registry: PolicyRegistry) -> None:
    def fixed_policy(params):
        action = params.get("action", 0)

        def decide(request):
            return {"decision": {"action": action}}

        return decide

    registry.register("fixed", fixed_policy)


def _agent_configs():
    return [
        PushAgentConfig(
            id="adversary_0",
            policy={"name": "fixed", "params": {"action": 0}},
            metadata={
                "explanation": "Hold position (noop) in push task.",
                "provenance": new_provenance(agent="adversary_0", sources=[]),
                "accountability": {
                    "owner": "team-a",
                    "policy_id": "policy-001",
                    "responsibility_scope": "simple-push",
                },
            },
        ),
        PushAgentConfig(
            id="agent_0",
            policy={"name": "fixed", "params": {"action": 1}},
            metadata={
                "explanation": "Move right in push task.",
                "provenance": new_provenance(agent="agent_0", sources=[]),
                "accountability": {
                    "owner": "team-b",
                    "policy_id": "policy-001",
                    "responsibility_scope": "simple-push",
                },
            },
        ),
    ]


class TestPushValidation(unittest.TestCase):
    def _make_external_env(self):
        try:
            return make_push_env(
                "pettingzoo:mpe2:simple_push_v3",
                {"max_cycles": 25, "continuous_actions": False, "dynamic_rescaling": False},
            )
        except ImportError as exc:
            raise unittest.SkipTest(str(exc)) from exc
        except ValueError as exc:
            raise unittest.SkipTest(str(exc)) from exc

    def test_validation_with_in_memory_adapter(self):
        shared_data = InMemorySharedData()
        env = self._make_external_env()
        registry = PolicyRegistry()
        _register_policies(registry)

        summary = run_push_validation(
            shared_data=shared_data,
            env=env,
            registry=registry,
            configs=_agent_configs(),
            rounds=3,
            seed=123,
        )

        decisions = list(shared_data.listen("decision"))
        explanations = list(shared_data.listen("explanation"))
        traces = list(shared_data.listen("trace"))
        outcomes = list(shared_data.listen("outcome"))

        self.assertEqual(summary.rounds, 3)
        self.assertEqual(summary.outcomes, 3)
        self.assertEqual(len(decisions), 6)
        self.assertEqual(len(explanations), 6)
        self.assertEqual(len(traces), 6)
        self.assertEqual(len(outcomes), 3)

        for record in decisions:
            self.assertTrue(record.accountability)

        for record in outcomes:
            self.assertIn("contributions", record.provenance)

    def test_validation_with_file_adapter(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "records.jsonl"
            shared_data = FileSharedData(path)
            env = self._make_external_env()
            registry = PolicyRegistry()
            _register_policies(registry)

            run_push_validation(
                shared_data=shared_data,
                env=env,
                registry=registry,
                configs=_agent_configs(),
                rounds=2,
                seed=321,
            )

            decisions = list(shared_data.listen("decision"))
            outcomes = list(shared_data.listen("outcome"))

            self.assertEqual(len(decisions), 4)
            self.assertEqual(len(outcomes), 2)
            self.assertGreater(output_bytes_from_path(path), 0)

    def test_baseline_run(self):
        shared_data = NoOpSharedData()
        env = self._make_external_env()
        registry = PolicyRegistry()
        _register_policies(registry)

        def run():
            run_push_validation(
                shared_data=shared_data,
                env=env,
                registry=registry,
                configs=_agent_configs(),
                rounds=2,
                seed=42,
            )

        metrics = measure_baseline(run)
        self.assertGreater(metrics.elapsed_seconds, 0)
        self.assertEqual(metrics.output_bytes, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
