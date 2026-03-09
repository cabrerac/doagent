"""Tests for simple push validation scenario."""

import tempfile
import unittest
from pathlib import Path

from doagent import make_env
from doagent.core import FileSharedData, InMemorySharedData
from doagent.validation import (
    NoOpSharedData,
    PolicyRegistry,
    measure_baseline,
    output_bytes_from_path,
    run_push_validation,
)
from examples.validation.push.env import create_push_env


def _register_policies(registry: PolicyRegistry) -> None:
    def fixed_policy(params):
        action = params.get("action", 0)

        def decide(request):
            return {"decision": {"action": action}}

        return decide

    registry.register("fixed", fixed_policy)


def _agent_configs():
    """Agent configs as plain dicts (Session API contract)."""
    return [
        {"id": "adversary_0", "policy": {"name": "fixed", "params": {"action": 0}}, "metadata": {"explanation": "Hold position (noop) in push task."}},
        {"id": "agent_0", "policy": {"name": "fixed", "params": {"action": 1}}, "metadata": {"explanation": "Move right in push task."}},
    ]


class TestPushValidation(unittest.TestCase):
    def _make_external_env(self):
        try:
            return make_env(
                create_push_env,
                max_cycles=25,
                continuous_actions=False,
                dynamic_rescaling=False,
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

        agent_updates = list(shared_data.listen("agent_update"))
        traces = list(shared_data.listen("trace"))
        outcomes = list(shared_data.listen("outcome"))

        self.assertEqual(summary.rounds, 3)
        self.assertEqual(summary.outcomes, 3)
        self.assertEqual(len(agent_updates), 6)
        self.assertEqual(len(traces), 6)
        self.assertEqual(len(outcomes), 3)

        for record in agent_updates:
            self.assertIn("decision", record.payload)
            self.assertIn("local_knowledge", record.payload)

        for record in outcomes:
            self.assertIn("created_by", record.provenance)

    def test_validation_with_file_adapter(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            shared_data = FileSharedData(temp_dir)
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

            agent_updates = list(shared_data.listen("agent_update"))
            outcomes = list(shared_data.listen("outcome"))

            self.assertEqual(len(agent_updates), 4)
            self.assertEqual(len(outcomes), 2)
            self.assertGreater(output_bytes_from_path(temp_dir), 0)

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
