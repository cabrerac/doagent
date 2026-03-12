"""Tests for the Session-based transparent API."""

import unittest

from doagent.core import InMemorySharedData, RunConfig, Session


class StubEnv:
    """Minimal env for testing the Session API."""

    def __init__(self, agent_ids, rounds=3):
        self._agent_ids = agent_ids
        self._round = 0

    @property
    def agents(self):
        return self._agent_ids

    def reset(self, *, seed=None):
        self._round = 0
        return {aid: {"pos": 0} for aid in self._agent_ids}

    def step(self, actions):
        self._round += 1
        obs = {aid: {"pos": self._round} for aid in self._agent_ids}
        rewards = {aid: 1.0 for aid in self._agent_ids}
        done = {aid: False for aid in self._agent_ids}
        return obs, rewards, done

    def render(self):
        pass


def _make_registry_and_configs(agent_ids):
    from doagent.core.policy import PolicyRegistry

    registry = PolicyRegistry()

    def fixed_policy(params):
        action = params.get("action", 0)
        def decide(request):
            return {
                "decision": {"action": action},
                "explanation": "test explanation",
            }
        return decide

    registry.register("fixed", fixed_policy)
    configs = [
        {"id": aid, "policy": {"name": "fixed", "params": {"action": i}}, "metadata": {}}
        for i, aid in enumerate(agent_ids)
    ]
    return registry, configs


class TestSession(unittest.TestCase):
    def test_basic_session_flow(self):
        shared_data = InMemorySharedData()
        session = Session(shared_data)
        env = session.wrap_env(StubEnv(["a", "b"]), env_actor="test_env")
        registry, configs = _make_registry_and_configs(["a", "b"])
        agents = session.create_agents(configs, registry)

        observations = env.reset(seed=42)
        self.assertIn("a", observations)

        for round_id in range(1, 4):
            actions = {}
            for aid, agent in agents.items():
                result = agent.decide(observations.get(aid, {}), round_id)
                actions[aid] = result["action"]
            step = env.step(actions)
            observations = step["observations"]

        agent_updates = list(shared_data.listen("agent_update"))
        outcomes = list(shared_data.listen("outcome"))
        traces = list(shared_data.listen("trace"))

        self.assertEqual(len(agent_updates), 6)
        self.assertEqual(len(outcomes), 3)
        self.assertEqual(len(traces), 6)

    def test_level_0_no_traces(self):
        shared_data = InMemorySharedData()
        session = Session(shared_data, RunConfig(logging_level=0))
        env = session.wrap_env(StubEnv(["a"]), env_actor="test_env")
        registry, configs = _make_registry_and_configs(["a"])
        agents = session.create_agents(configs, registry)

        observations = env.reset(seed=1)
        for round_id in range(1, 3):
            actions = {}
            for aid, agent in agents.items():
                result = agent.decide(observations.get(aid, {}), round_id)
                actions[aid] = result["action"]
            step = env.step(actions)
            observations = step["observations"]

        agent_updates = list(shared_data.listen("agent_update"))
        traces = list(shared_data.listen("trace"))
        outcomes = list(shared_data.listen("outcome"))

        self.assertEqual(len(agent_updates), 2)
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(len(traces), 0)

        for rec in agent_updates:
            self.assertNotIn("explanation", rec.payload.get("decision", {}))

    def test_level_2_includes_provenance_and_accountability(self):
        shared_data = InMemorySharedData()
        session = Session(shared_data, RunConfig(logging_level=2))
        env = session.wrap_env(StubEnv(["a"]), env_actor="test_env")
        registry, configs = _make_registry_and_configs(["a"])
        agents = session.create_agents(configs, registry)

        observations = env.reset(seed=1)
        result = agents["a"].decide(observations["a"], 1)
        actions = {"a": result["action"]}
        env.step(actions)

        agent_updates = list(shared_data.listen("agent_update"))
        outcomes = list(shared_data.listen("outcome"))

        self.assertEqual(len(agent_updates), 1)
        self.assertIn("created_by", agent_updates[0].provenance)
        self.assertIn("owner", agent_updates[0].accountability)
        self.assertIn("created_by", outcomes[0].provenance)

    def test_record_decision_for_external_policy(self):
        shared_data = InMemorySharedData()
        session = Session(shared_data)
        env = session.wrap_env(StubEnv(["a"]), env_actor="test_env")

        observations = env.reset(seed=1)
        external_response = {"decision": {"action": 42}}
        session.record_decision("a", observations["a"], external_response, 1)
        env.step({"a": 42})

        agent_updates = list(shared_data.listen("agent_update"))
        outcomes = list(shared_data.listen("outcome"))
        traces = list(shared_data.listen("trace"))

        self.assertEqual(len(agent_updates), 1)
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(len(traces), 1)

    def test_record_update_for_hub_summary(self):
        shared_data = InMemorySharedData()
        session = Session(shared_data)
        env = session.wrap_env(StubEnv(["a"]), env_actor="test_env")
        registry, configs = _make_registry_and_configs(["a"])
        agents = session.create_agents(configs, registry)

        observations = env.reset(seed=1)
        result = agents["a"].decide(observations["a"], 1)
        session.record_update("hub", {"cells": []}, payload_type="map_summary")
        env.step({"a": result["action"]})

        all_updates = list(shared_data.listen("agent_update"))
        hub_updates = [r for r in all_updates if r.actor == "hub"]
        self.assertEqual(len(hub_updates), 1)
        self.assertEqual(hub_updates[0].payload.get("type"), "map_summary")

    def test_custom_step_adapter(self):
        shared_data = InMemorySharedData()
        session = Session(shared_data)

        class DictEnv:
            agents = ["a"]
            def reset(self, *, seed=None):
                return {"a": {"x": 0}}
            def step(self, actions):
                return {"obs": {"a": {"x": 1}}, "rew": {"a": 1.0}, "finished": {}}

        adapter = lambda r: {
            "observations": r["obs"],
            "rewards": r["rew"],
            "done": r["finished"],
        }
        env = session.wrap_env(DictEnv(), env_actor="custom", adapter=adapter)
        registry, configs = _make_registry_and_configs(["a"])
        agents = session.create_agents(configs, registry)

        observations = env.reset(seed=1)
        result = agents["a"].decide(observations["a"], 1)
        step = env.step({"a": result["action"]})

        self.assertIn("a", step["observations"])
        outcomes = list(shared_data.listen("outcome"))
        self.assertEqual(len(outcomes), 1)

    def test_wrap_env_before_create_agents(self):
        shared_data = InMemorySharedData()
        session = Session(shared_data)
        registry, configs = _make_registry_and_configs(["a"])
        with self.assertRaises(RuntimeError):
            session.create_agents(configs, registry)

    # -- Decentralisation: visible_records with topology --

    def _run_two_agent_round(self, session):
        """Helper: run one round with agents a and b, return session."""
        env = session.wrap_env(StubEnv(["a", "b"]), env_actor="test_env")
        registry, configs = _make_registry_and_configs(["a", "b"])
        agents = session.create_agents(configs, registry)
        observations = env.reset(seed=1)
        actions = {}
        for aid, agent in agents.items():
            result = agent.decide(observations.get(aid, {}), 1)
            actions[aid] = result["action"]
        env.step(actions)
        return session

    def test_visible_records_centralised_sees_all(self):
        from doagent.core import TopologyConfig, Topology
        shared_data = InMemorySharedData()
        session = Session(
            shared_data, topology=TopologyConfig(mode=Topology.CENTRALISED),
        )
        self._run_two_agent_round(session)

        records_a = session.visible_records("a", kind="agent_update")
        records_b = session.visible_records("b", kind="agent_update")

        self.assertEqual(len(records_a), 2)
        self.assertEqual(len(records_b), 2)

    def test_visible_records_peer_to_peer_filtered(self):
        from doagent.core import TopologyConfig, Topology
        shared_data = InMemorySharedData()
        session = Session(
            shared_data,
            topology=TopologyConfig(mode=Topology.PEER_TO_PEER),
            visibility={"a": ["b"]},
        )
        self._run_two_agent_round(session)

        records_a = session.visible_records("a", kind="agent_update")
        records_b = session.visible_records("b", kind="agent_update")

        self.assertEqual(len(records_a), 2)
        self.assertEqual(len(records_b), 1)
        self.assertEqual(records_b[0].actor, "b")

    def test_visible_records_federated_agents_see_hub_only(self):
        from doagent.core import TopologyConfig, Topology
        shared_data = InMemorySharedData()
        session = Session(
            shared_data,
            topology=TopologyConfig(mode=Topology.FEDERATED),
            hub_id="hub",
        )
        self._run_two_agent_round(session)
        session.record_update("hub", {"summary": True}, payload_type="hub_summary")

        records_a = session.visible_records("a", kind="agent_update")
        records_hub = session.visible_records("hub", kind="agent_update")

        self.assertEqual(len(records_a), 1)
        self.assertEqual(records_a[0].actor, "hub")
        self.assertEqual(len(records_hub), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
