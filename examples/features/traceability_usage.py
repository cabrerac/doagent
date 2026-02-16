"""Traceability records example."""

from doagent.core import (
    InMemorySharedData,
    new_agent_update_record,
    new_record,
    new_trace_record,
)
def main() -> None:
    shared_data = InMemorySharedData()

    from_outcome = new_record(
        actor="env",
        kind="outcome",
        payload={"round": 0, "observations": {}},
    )
    shared_data.write(from_outcome)

    agent_update = new_agent_update_record(
        actor="agent-1",
        local_knowledge={"observation": {}},
        decision={"request": {}, "response": {"decision": {"action": "move"}}},
    )
    shared_data.write(agent_update)

    to_outcome = new_record(
        actor="env",
        kind="outcome",
        payload={"round": 1, "observations": {}, "rewards": {}},
    )
    shared_data.write(to_outcome)

    trace = new_trace_record(
        actor="agent-1",
        from_id=from_outcome.id,
        to_id=to_outcome.id,
        enabled_by_id=agent_update.id,
        relation="enables",
        round_=1,
        notes="Agent decision enabled transition.",
    )
    shared_data.write(trace)

    record = list(shared_data.listen("trace"))[0]
    assert record.payload["from_id"] == from_outcome.id
    assert record.payload["to_id"] == to_outcome.id
    assert record.payload["enabled_by_id"] == agent_update.id


if __name__ == "__main__":
    main()
