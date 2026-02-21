"""Model-agnostic agent example using the Session API.

Any callable that returns {"decision": {"action": ...}} works as a policy.
"""

from doagent import Session, InMemorySharedData
from doagent.validation import PolicyRegistry


def main() -> None:
    shared_data = InMemorySharedData()

    def custom_policy(params):
        def decide(request):
            goal = request.get("goal", "no-goal")
            return {"decision": {"action": "log", "message": goal}}
        return decide

    registry = PolicyRegistry()
    registry.register("custom", custom_policy)

    class StubEnv:
        agents = ["agent-1"]
        def reset(self, *, seed=None):
            return {"agent-1": {"goal": "store a decision"}}
        def step(self, actions):
            return {"agent-1": {}}, {"agent-1": 0.0}, {}

    # doagent: session handles recording transparently
    session = Session(shared_data)
    env = session.wrap_env(StubEnv(), env_actor="stub_env")
    agents = session.create_agents(
        [{"id": "agent-1", "policy": {"name": "custom", "params": {}}}],
        registry,
        goal="store a decision",
    )

    observations = env.reset(seed=1)
    result = agents["agent-1"].decide(observations["agent-1"], round_id=1)
    env.step({"agent-1": result["action"]})

    # doagent: inspect recorded agent_update
    record = list(shared_data.listen("agent_update"))[0]
    assert record.payload["decision"]["response"]["decision"]["action"] == "log"


if __name__ == "__main__":
    main()
