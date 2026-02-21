"""Minimal DOAgent usage example using the Session API."""

from doagent import Session, InMemorySharedData
from doagent.validation import PolicyRegistry


def main() -> None:
    # doagent: create session with in-memory adapter
    shared_data = InMemorySharedData()
    session = Session(shared_data)

    class StubEnv:
        agents = ["agent-1"]
        def reset(self, *, seed=None):
            return {"agent-1": {"text": "Hello from DOAgent"}}
        def step(self, actions):
            return {"agent-1": {"text": "Step complete"}}, {"agent-1": 0.0}, {}

    registry = PolicyRegistry()
    registry.register("noop", lambda params: lambda req: {"decision": {"action": 0}})

    # doagent: wrap env and create agents
    env = session.wrap_env(StubEnv(), env_actor="stub_env")
    agents = session.create_agents(
        [{"id": "agent-1", "policy": {"name": "noop", "params": {}}}],
        registry,
    )

    # doagent: reset, decide, step — recording happens transparently
    observations = env.reset(seed=42)
    result = agents["agent-1"].decide(observations["agent-1"], round_id=1)
    env.step({"agent-1": result["action"]})

    # doagent: records are accessible via shared_data
    for record in shared_data.list():
        assert shared_data.read(record.id) is not None

    agent_updates = list(shared_data.listen("agent_update"))
    outcomes = list(shared_data.listen("outcome"))
    assert len(agent_updates) == 1
    assert len(outcomes) == 1


if __name__ == "__main__":
    main()
