"""Minimal DOAgent usage example."""

from doagent.core import InMemorySharedData, StubAgent


def main() -> None:
    shared_data = InMemorySharedData()
    agent = StubAgent("agent-1", shared_data)

    record = agent.write(kind="note", payload={"text": "Hello from DOAgent"})

    for seen in shared_data.listen("note"):
        record_read = agent.read(seen.id)
        assert record_read is not None

    assert record.id in [seen.id for seen in shared_data.list()]


if __name__ == "__main__":
    main()
