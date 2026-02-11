"""Model-agnostic agent example."""

from doagent.core import FunctionAgent, InMemorySharedData


def decide_fn(request: dict) -> dict:
    goal = request.get("goal", "no-goal")
    return {"decision": {"action": "log", "message": goal}}


def main() -> None:
    shared_data = InMemorySharedData()
    agent = FunctionAgent("agent-1", shared_data, decide_fn)

    request = {"id": "req-1", "actor": "agent-1", "goal": "store a decision"}
    response = agent.decide(request)

    record = list(shared_data.listen("decision"))[0]
    assert record.payload["response"]["id"] == response["id"]
    assert record.payload["request"]["id"] == "req-1"


if __name__ == "__main__":
    main()
