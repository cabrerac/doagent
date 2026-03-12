"""Tests for trace graph construction and state deduplication."""

import unittest
from typing import Any, Dict

from doagent.core import InMemorySharedData, RunConfig, Session
from doagent.core import FileSharedData
from doagent.core import default_state_hash
from doagent.records import INITIAL_STATE_ID
from doagent.core import PolicyRegistry


class CyclingEnv:
    """Env that cycles through a fixed sequence of states, enabling dedup testing.

    States cycle: S0 -> S1 -> S2 -> S0 -> S1 -> ...
    """

    def __init__(self, agent_ids, states=None):
        self._agent_ids = agent_ids
        self._states = states or [
            {aid: {"pos": 0} for aid in agent_ids},
            {aid: {"pos": 1} for aid in agent_ids},
            {aid: {"pos": 2} for aid in agent_ids},
        ]
        self._step_count = 0

    @property
    def agents(self):
        return self._agent_ids

    def reset(self, *, seed=None):
        self._step_count = 0
        return dict(self._states[0])

    def step(self, actions):
        self._step_count += 1
        idx = self._step_count % len(self._states)
        obs = dict(self._states[idx])
        rewards = {aid: 0.0 for aid in self._agent_ids}
        done = {aid: False for aid in self._agent_ids}
        return obs, rewards, done


def _make_registry_and_configs(agent_ids):
    registry = PolicyRegistry()

    def fixed_policy(params):
        def decide(request):
            return {"decision": {"action": 0}}
        return decide

    registry.register("fixed", fixed_policy)
    configs = [
        {"id": aid, "policy": {"name": "fixed", "params": {}}, "metadata": {}}
        for aid in agent_ids
    ]
    return registry, configs


def _state_only_hash(payload: Dict[str, Any]) -> str:
    """Hash only observations, ignoring done/round/actions/rewards."""
    state_content = {"observations": payload.get("observations", {})}
    return default_state_hash(state_content)


def _full_payload_hash(payload: Dict[str, Any]) -> str:
    """Hash the entire payload including round — never deduplicates across rounds."""
    import hashlib
    import json
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _collect_records(shared_data, kind):
    return list(shared_data.listen(kind))


def _run_session(shared_data, rounds, state_hash_fn=None):
    """Run a cycling env for N rounds through a Session, return shared_data."""
    agent_ids = ["agent_0", "agent_1"]
    session = Session(
        shared_data,
        RunConfig(logging_level=1),
        state_hash_fn=state_hash_fn,
    )
    env = session.wrap_env(CyclingEnv(agent_ids), env_actor="cycling_env")
    registry, configs = _make_registry_and_configs(agent_ids)
    agents = session.create_agents(configs, registry)

    observations = env.reset()
    for round_id in range(1, rounds + 1):
        actions = {}
        for aid, agent in agents.items():
            result = agent.decide(observations.get(aid, {}), round_id)
            actions[aid] = result["action"]
        step = env.step(actions)
        observations = step["observations"]
    return shared_data


class TestTraceGraph(unittest.TestCase):
    """Tests for trace graph structure (no dedup)."""

    def test_first_trace_has_initial_state_from_id(self):
        shared_data = _run_session(InMemorySharedData(), rounds=2)
        traces = _collect_records(shared_data, "trace")
        self.assertGreater(len(traces), 0)
        first_trace = traces[0]
        self.assertEqual(first_trace.payload["from_id"], INITIAL_STATE_ID)

    def test_trace_chain_valid_transitions(self):
        shared_data = _run_session(InMemorySharedData(), rounds=3)
        traces = _collect_records(shared_data, "trace")
        outcomes = _collect_records(shared_data, "outcome")
        outcome_ids = {r.id for r in outcomes}

        for trace in traces:
            from_id = trace.payload["from_id"]
            to_id = trace.payload["to_id"]
            enabled_by = trace.payload["enabled_by_id"]
            self.assertTrue(
                from_id == INITIAL_STATE_ID or from_id in outcome_ids,
                f"from_id {from_id} not found in outcomes",
            )
            self.assertIn(to_id, outcome_ids)
            self.assertIsNotNone(enabled_by)

    def test_traces_reference_agent_updates(self):
        shared_data = _run_session(InMemorySharedData(), rounds=2)
        traces = _collect_records(shared_data, "trace")
        agent_updates = _collect_records(shared_data, "agent_update")
        update_ids = {r.id for r in agent_updates}

        for trace in traces:
            self.assertIn(trace.payload["enabled_by_id"], update_ids)

    def test_outcomes_without_dedup_are_all_unique(self):
        shared_data = _run_session(InMemorySharedData(), rounds=6)
        outcomes = _collect_records(shared_data, "outcome")
        outcome_ids = [r.id for r in outcomes]
        self.assertEqual(len(outcome_ids), len(set(outcome_ids)))
        self.assertEqual(len(outcomes), 6)


class TestStateDedup(unittest.TestCase):
    """Tests for state deduplication when state_hash_fn is provided."""

    def test_equivalent_states_deduplicate(self):
        """Cycling env revisits states; dedup should reuse outcome ids."""
        shared_data = _run_session(
            InMemorySharedData(), rounds=6, state_hash_fn=_state_only_hash,
        )
        outcomes = _collect_records(shared_data, "outcome")
        # 3 unique states (cycle length 3), 6 rounds -> 3 outcomes stored
        self.assertEqual(len(outcomes), 3)

    def test_multiple_traces_point_to_same_outcome(self):
        """When state is reused, different traces share the same to_id."""
        shared_data = _run_session(
            InMemorySharedData(), rounds=6, state_hash_fn=_state_only_hash,
        )
        traces = _collect_records(shared_data, "trace")
        to_ids = [t.payload["to_id"] for t in traces]
        # With 2 agents and 6 rounds, we get 12 traces. to_ids should repeat.
        self.assertGreater(len(to_ids), len(set(to_ids)))

    def test_dedup_traces_still_reference_initial_state(self):
        shared_data = _run_session(
            InMemorySharedData(), rounds=6, state_hash_fn=_state_only_hash,
        )
        traces = _collect_records(shared_data, "trace")
        first_round_traces = [t for t in traces if t.payload.get("round") == 1]
        for t in first_round_traces:
            self.assertEqual(t.payload["from_id"], INITIAL_STATE_ID)

    def test_default_hash_deduplicates_cycling_states(self):
        """default_state_hash hashes only state fields, so cycling states deduplicate."""
        shared_data = _run_session(
            InMemorySharedData(), rounds=6, state_hash_fn=default_state_hash,
        )
        outcomes = _collect_records(shared_data, "outcome")
        self.assertEqual(len(outcomes), 3)

    def test_full_payload_hash_prevents_dedup(self):
        """A hash that includes round/actions/rewards prevents dedup across rounds."""
        shared_data = _run_session(
            InMemorySharedData(), rounds=6, state_hash_fn=_full_payload_hash,
        )
        outcomes = _collect_records(shared_data, "outcome")
        self.assertEqual(len(outcomes), 6)

    def test_adapter_index_populated(self):
        shared_data = InMemorySharedData()
        _run_session(shared_data, rounds=6, state_hash_fn=_state_only_hash)
        self.assertEqual(len(shared_data._state_index), 3)

    def test_file_adapter_dedup(self):
        """FileSharedData also supports dedup via in-memory index."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            shared_data = FileSharedData(tmpdir)
            _run_session(shared_data, rounds=6, state_hash_fn=_state_only_hash)

            outcomes = list(shared_data.listen("outcome"))
            self.assertEqual(len(outcomes), 3)

            traces = list(shared_data.listen("trace"))
            to_ids = [t.payload["to_id"] for t in traces]
            self.assertGreater(len(to_ids), len(set(to_ids)))


class TestNoHashFnNoDedup(unittest.TestCase):
    """Without state_hash_fn, dedup is completely off."""

    def test_no_hash_fn_every_outcome_unique(self):
        shared_data = _run_session(InMemorySharedData(), rounds=6)
        outcomes = _collect_records(shared_data, "outcome")
        self.assertEqual(len(outcomes), 6)

    def test_no_hash_fn_index_stays_empty(self):
        shared_data = InMemorySharedData()
        _run_session(shared_data, rounds=6)
        self.assertEqual(len(shared_data._state_index), 0)


if __name__ == "__main__":
    unittest.main()
