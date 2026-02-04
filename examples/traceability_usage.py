"""Traceability records example."""

from doagent.core import InMemorySharedData, new_record, new_trace_record


def main() -> None:
    shared_data = InMemorySharedData()

    upstream = new_record(
        actor="agent-1",
        kind="note",
        payload={"text": "source"},
    )
    downstream = new_record(
        actor="agent-2",
        kind="decision",
        payload={"decision": {"action": "use"}},
    )
    shared_data.write(upstream)
    shared_data.write(downstream)

    trace = new_trace_record(
        actor="agent-2",
        from_id=upstream.id,
        to_id=downstream.id,
        relation="used",
        notes="Decision used upstream note.",
    )
    shared_data.write(trace)

    record = list(shared_data.listen("trace"))[0]
    assert record.payload["from_id"] == upstream.id
    assert record.payload["to_id"] == downstream.id


if __name__ == "__main__":
    main()
