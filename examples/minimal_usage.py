"""Minimal DOAgent usage example using the Session API (config-driven).

Run from repo root: python -m examples.minimal_usage
"""

from __future__ import annotations

from doagent import Session


def main() -> None:
    # Session with in-memory shared_data so we can inspect records after the run
    session = Session.from_config({
        "shared_data": {"type": "memory"},
        "run_config": {"logging_level": 2},
        "topology": {"mode": "centralised"},
        "policies": {
            "noop": lambda params: lambda req: {"choice": {"status": "act", "action": 0}},
        },
    })

    class StubEnv:
        agents = ["agent-1"]

        def reset(self, *, seed=None):
            return {"agent-1": {"text": "Hello from DOAgent"}}

        def step(self, actions):
            return {
                "observations": {"agent-1": {"text": "Step complete"}},
                "rewards": {"agent-1": 0.0},
                "terminations": {"agent-1": False},
            }

    env = session.wrap_env(StubEnv(), env_actor="stub_env")
    agents = session.create_agents(
        [{"id": "agent-1", "policy": {"name": "noop", "params": {}}}],
        goal="demo",
        payload_type="demo_update",
    )

    observations = env.reset(seed=42)
    result = agents["agent-1"].decide(observations["agent-1"], 1, inputs={})
    env.step({"agent-1": result["action"]})

    # Inspect recorded kinds
    agent_updates = session.inspect("agent_update")
    outcomes = session.inspect("outcome")
    assert len(agent_updates) == 1
    assert len(outcomes) == 1


if __name__ == "__main__":
    main()
