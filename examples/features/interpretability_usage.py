"""Interpretability records example."""

from doagent.core import InMemorySharedData, new_agent_update_record


def main() -> None:
    shared_data = InMemorySharedData()

    agent_update = new_agent_update_record(
        actor="agent-1",
        local_knowledge={"observation": {}},
        decision={
            "request": {},
            "response": {"decision": {"action": "approve"}},
            "explanation": "Approved due to policy compliance.",
        },
    )
    shared_data.write(agent_update)

    record = list(shared_data.listen("agent_update"))[0]
    decision = record.payload["decision"]
    assert decision["explanation"] == "Approved due to policy compliance."


if __name__ == "__main__":
    main()
