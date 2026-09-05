"""Tests for the Session-based transparent API."""

import json
import tempfile
import unittest
from pathlib import Path

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
    from doagent.core import PolicyRegistry

    registry = PolicyRegistry()

    def fixed_policy(params):
        action = params.get("action", 0)
        def decide(request):
            return {
                "choice": {"status": "act", "action": action},
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
    def test_register_and_deregister_participant_via_session_api(self):
        session = Session.from_config({
            "shared_data": {"type": "memory"},
            "participation": True,
        })
        self.assertIsNotNone(session.participation_registry)

        class AgentObj:
            def __init__(self, agent_id: str):
                self.agent_id = agent_id

        session.register_participant("agent_str", capabilities=["map"])
        session.register_participant({"id": "agent_dict"}, capabilities=["map"])
        session.register_participant(AgentObj("agent_obj"), capabilities=["map"])

        registry = session.participation_registry
        ids = sorted(r.agent_id for r in registry.list())
        self.assertEqual(ids, ["agent_dict", "agent_obj", "agent_str"])

        session.deregister_participant("agent_dict")
        ids_after = sorted(r.agent_id for r in registry.list())
        self.assertEqual(ids_after, ["agent_obj", "agent_str"])

        events = session.inspect("participation")
        self.assertEqual(len(events), 4)
        self.assertEqual(
            [r.payload["event"] for r in events],
            ["join", "join", "join", "leave"],
        )
        self.assertEqual(
            [r.actor for r in events],
            ["agent_str", "agent_dict", "agent_obj", "agent_dict"],
        )
        self.assertEqual(events[0].kind, "participation")
        self.assertEqual(events[0].payload["capabilities"], ["map"])
        self.assertEqual(events[-1].payload["event"], "leave")
        self.assertEqual(events[-1].payload["capabilities"], ["map"])
        self.assertEqual(events[0].provenance.get("created_by"), "agent_str")

    def test_participation_events_persist_to_file(self):
        """File adapter stores participation as participation.jsonl like any other kind."""
        with tempfile.TemporaryDirectory() as tmp:
            records_dir = Path(tmp)
            session = Session.from_config({
                "shared_data": {"type": "file", "path": str(records_dir)},
                "participation": True,
            })
            session.register_participant(
                "agent_a",
                capabilities=["map"],
                resource_limits={"cpu": 1.0},
            )
            session.deregister_participant("agent_a")

            path = records_dir / "participation.jsonl"
            self.assertTrue(path.is_file())
            events = session.inspect("participation")
            self.assertEqual(len(events), 2)
            self.assertEqual([r.payload["event"] for r in events], ["join", "leave"])
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)
            parsed = [json.loads(line) for line in lines]
            self.assertEqual(parsed[0]["kind"], "participation")
            self.assertEqual(parsed[0]["payload"]["event"], "join")
            self.assertEqual(parsed[1]["payload"]["event"], "leave")

    def test_participation_events_follow_logging_levels(self):
        """Events are written at every level; envelope provenance starts at level 1."""
        for level, expect_provenance in ((0, False), (1, True), (2, True)):
            with self.subTest(logging_level=level):
                session = Session.from_config({
                    "shared_data": {"type": "memory"},
                    "participation": True,
                    "run_config": {"logging_level": level},
                })
                session.register_participant("agent_a", capabilities=["map"])
                events = session.inspect("participation")
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0].payload["event"], "join")
                if expect_provenance:
                    self.assertEqual(events[0].provenance.get("created_by"), "agent_a")
                    self.assertEqual(events[0].accountability.get("owner"), "agent_a")
                else:
                    self.assertEqual(events[0].provenance, {})
                    self.assertEqual(events[0].accountability, {})

    def test_visible_participants_centralised_sees_all_current_members(self):
        session = Session.from_config({
            "shared_data": {"type": "memory"},
            "participation": True,
            "topology": {"mode": "centralised"},
        })
        session.register_participant("a", capabilities=["map"])
        session.register_participant("b", capabilities=["map"])
        session.register_participant("c", capabilities=["search"])
        session.deregister_participant("c")
        ids = sorted(p["agent_id"] for p in session.visible_participants("a"))
        self.assertEqual(ids, ["a", "b"])

    def test_visible_participants_peer_to_peer_meshes_unlisted_only(self):
        """YAML holds for named agents; only a stranger is meshed in."""
        session = Session.from_config({
            "shared_data": {"type": "memory"},
            "participation": True,
            "topology": {
                "mode": "peer_to_peer",
                "visibility": {"a": ["b"]},
            },
        })
        session.register_participant("a", capabilities=["map"])
        session.register_participant("b", capabilities=["map"])
        session.register_participant("c", capabilities=["search"])
        ids_a = sorted(p["agent_id"] for p in session.visible_participants("a"))
        ids_b = sorted(p["agent_id"] for p in session.visible_participants("b"))
        ids_c = sorted(p["agent_id"] for p in session.visible_participants("c"))
        self.assertEqual(ids_a, ["a", "b", "c"])
        self.assertEqual(ids_b, ["b", "c"])
        self.assertEqual(ids_c, ["a", "b", "c"])

    def test_p2p_leave_hides_leaver_records(self):
        session = Session.from_config({
            "shared_data": {"type": "memory"},
            "participation": True,
            "topology": {"mode": "peer_to_peer"},
        })
        session.register_participant("a")
        session.register_participant("b")
        session.record_update("a", {"x": 1})
        session.record_update("b", {"x": 2})
        actors_before = {r.actor for r in session.visible_records("a", kind="agent_update")}
        self.assertEqual(actors_before, {"a", "b"})
        session.deregister_participant("b")
        actors_after = {r.actor for r in session.visible_records("a", kind="agent_update")}
        self.assertEqual(actors_after, {"a"})
        ids_a = sorted(p["agent_id"] for p in session.visible_participants("a"))
        self.assertEqual(ids_a, ["a"])

    def test_p2p_custom_membership_hook_keeps_yaml(self):
        def keep_yaml(event, agent_id, members, visibility):
            return {key: list(peers) for key, peers in visibility.items()}

        session = Session.from_config({
            "shared_data": {"type": "memory"},
            "participation": True,
            "topology": {
                "mode": "peer_to_peer",
                "visibility": {"a": ["b"]},
                "on_membership_change": keep_yaml,
            },
        })
        session.register_participant("a", capabilities=["map"])
        session.register_participant("b", capabilities=["map"])
        session.register_participant("c", capabilities=["search"])
        ids_a = sorted(p["agent_id"] for p in session.visible_participants("a"))
        ids_c = sorted(p["agent_id"] for p in session.visible_participants("c"))
        self.assertEqual(ids_a, ["a", "b"])
        self.assertEqual(ids_c, ["c"])

    def test_p2p_listed_agents_keep_yaml_links(self):
        session = Session.from_config({
            "shared_data": {"type": "memory"},
            "participation": True,
            "topology": {
                "mode": "peer_to_peer",
                "visibility": {"a": ["b"]},
            },
        })
        session.register_participant("a")
        session.register_participant("b")
        ids_a = sorted(p["agent_id"] for p in session.visible_participants("a"))
        ids_b = sorted(p["agent_id"] for p in session.visible_participants("b"))
        self.assertEqual(ids_a, ["a", "b"])
        self.assertEqual(ids_b, ["b"])

    def test_visible_participants_federated_uses_hub_roster(self):
        session = Session.from_config({
            "shared_data": {"type": "memory"},
            "participation": True,
            "topology": {"mode": "federated"},
            "hub_id": "hub",
        })
        session.register_participant("a", capabilities=["map"])
        session.register_participant("b", capabilities=["map"])
        ids_a = sorted(p["agent_id"] for p in session.visible_participants("a"))
        self.assertEqual(ids_a, ["a", "b"])
        rosters = [
            r for r in session.inspect("participation")
            if r.payload.get("event") == "roster"
        ]
        self.assertTrue(rosters)
        self.assertEqual(rosters[-1].actor, "hub")
        session.deregister_participant("b")
        ids_after = sorted(p["agent_id"] for p in session.visible_participants("a"))
        self.assertEqual(ids_after, ["a"])

    def test_federated_hub_hook_noop_writes_nothing(self):
        def noop(event, agent_id, members, hub_id):
            return []

        session = Session.from_config({
            "shared_data": {"type": "memory"},
            "participation": True,
            "topology": {
                "mode": "federated",
                "on_hub_membership": noop,
            },
            "hub_id": "hub",
        })
        session.register_participant("a")
        session.register_participant("b")
        self.assertEqual(session.visible_participants("a"), [])
        rosters = [
            r for r in session.inspect("participation")
            if r.payload.get("event") == "roster"
        ]
        self.assertEqual(rosters, [])

    def test_federated_hub_relay_join_leave(self):
        from doagent.core.topology import relay_join_leave_as_hub

        session = Session.from_config({
            "shared_data": {"type": "memory"},
            "participation": True,
            "topology": {
                "mode": "federated",
                "on_hub_membership": relay_join_leave_as_hub,
            },
            "hub_id": "hub",
        })
        session.register_participant("a", capabilities=["map"])
        session.register_participant("b", capabilities=["map"])
        ids_a = sorted(p["agent_id"] for p in session.visible_participants("a"))
        self.assertEqual(ids_a, ["a", "b"])
        rosters = [
            r for r in session.inspect("participation")
            if r.payload.get("event") == "roster"
        ]
        self.assertEqual(rosters, [])
        hub_joins = [
            r for r in session.inspect("participation")
            if r.actor == "hub" and r.payload.get("event") == "join"
        ]
        self.assertEqual(len(hub_joins), 2)
        session.deregister_participant("b")
        ids_after = sorted(p["agent_id"] for p in session.visible_participants("a"))
        self.assertEqual(ids_after, ["a"])

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

    def test_from_config_with_scenario_name_creates_run_folders_and_metadata(self):
        """When scenario_name and file storage are set, library creates run_id, folders, and metadata.json."""
        with tempfile.TemporaryDirectory() as tmp:
            config = {
                "shared_data": {"type": "file"},
                "scenario_name": "gridworld",
                "output_base": tmp,
                "run_config": {"logging_level": 0},
            }
            session = Session.from_config(config)
            self.assertIsNotNone(session.run_id)
            self.assertIsNotNone(session.run_path)
            self.assertTrue(session.run_id.startswith("gridworld_run_"))
            run_path = Path(session.run_path)
            self.assertTrue(run_path.is_dir())
            records_dir = run_path / "records"
            self.assertTrue(records_dir.is_dir())
            metadata_path = run_path / "metadata.json"
            self.assertTrue(metadata_path.is_file())
            with metadata_path.open("r", encoding="utf-8") as f:
                metadata = json.load(f)
            self.assertEqual(metadata["run_id"], session.run_id)
            self.assertEqual(metadata["scenario_name"], "gridworld")
            self.assertEqual(metadata["storage_type"], "file")
            self.assertEqual(metadata["metadata_schema_version"], 1)
            self.assertEqual(metadata["records_dir"], "records")
            self.assertIn("created_at", metadata)

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
        external_response = {"choice": {"status": "act", "action": 42}}
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

    def test_decision_context_kinds_last_n_and_summarise(self):
        session = Session.from_config({
            "shared_data": {"type": "memory"},
            "topology": {"mode": "centralised"},
        })
        session.record_update("a", {"n": 1})
        session.record_update("b", {"n": 2})
        session.record_update("a", {"n": 3})

        all_updates = session.decision_context("a", kinds="agent_update")
        self.assertEqual(len(all_updates), 3)

        last_two = session.decision_context("a", kinds="agent_update", last_n=2)
        self.assertEqual(len(last_two), 2)
        self.assertEqual(last_two[0].payload["local_knowledge"]["n"], 2)
        self.assertEqual(last_two[1].payload["local_knowledge"]["n"], 3)

        none = session.decision_context("a", kinds="agent_update", last_n=0)
        self.assertEqual(none, [])

        mixed = session.decision_context("a", kinds=["agent_update", "participation"])
        self.assertEqual(len(mixed), 3)

        def count_records(records):
            return len(records)

        self.assertEqual(
            session.decision_context("a", kinds="agent_update", summarise=count_records),
            3,
        )
        with self.assertRaises(ValueError):
            session.decision_context("a", last_n=-1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
