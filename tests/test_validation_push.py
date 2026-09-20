"""Tests for simple push validation scenario.

Use only the public API: Session.from_config, make_env, session.inspect.
"""

import tempfile
import unittest
from pathlib import Path

from doagent import Session, make_env
from examples.push.env import create_push_env
from examples.push.session import run_with_session
from experiments import measure_baseline, output_bytes_from_path


def _fixed_policy(params):
    action = params.get("action", 0)

    def decide(request):
        return {"choice": {"status": "act", "action": action}}

    return decide


def _agent_configs():
    """Agent configs as plain dicts (Session API contract)."""
    return [
        {"id": "adversary_0", "policy": {"name": "fixed", "params": {"action": 0}}, "metadata": {"explanation": "Hold position (noop) in push task."}},
        {"id": "agent_0", "policy": {"name": "fixed", "params": {"action": 1}}, "metadata": {"explanation": "Move right in push task."}},
    ]


def _session_config(shared_data_type: str = "memory", path: str | None = None) -> dict:
    cfg = {
        "shared_data": {"type": shared_data_type},
        "run_config": {"logging_level": 2},
        "topology": {"mode": "centralised"},
        "policies": {"fixed": _fixed_policy},
    }
    if path is not None:
        cfg["shared_data"]["path"] = path
    return cfg


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
        config = _session_config("memory")
        session = Session.from_config(config)
        env = self._make_external_env()

        outcome_count = run_with_session(
            session,
            env,
            _agent_configs(),
            3,
            123,
        )

        agent_updates = session.inspect("agent_update")
        traces = session.inspect("trace")
        outcomes = session.inspect("outcome")

        self.assertEqual(outcome_count, 3)
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
            config = _session_config("file", path=temp_dir)
            session = Session.from_config(config)
            env = self._make_external_env()

            run_with_session(
                session,
                env,
                _agent_configs(),
                2,
                321,
            )

            agent_updates = session.inspect("agent_update")
            outcomes = session.inspect("outcome")

            self.assertEqual(len(agent_updates), 4)
            self.assertEqual(len(outcomes), 2)
            session.close()
            self.assertGreater(output_bytes_from_path(temp_dir), 0)

    def test_baseline_run(self):
        config = _session_config("noop")
        session = Session.from_config(config)
        env = self._make_external_env()

        def run():
            run_with_session(
                session,
                env,
                _agent_configs(),
                2,
                42,
            )

        metrics = measure_baseline(run)
        self.assertGreater(metrics.elapsed_seconds, 0)
        self.assertEqual(metrics.output_bytes, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
