"""Provenance helper example."""

from doagent.core import InMemorySharedData, new_record
from doagent.records import new_provenance


def main() -> None:
    shared_data = InMemorySharedData()

    provenance = new_provenance(
        agent="agent-1",
        sources=["r1", "r2"],
        tools=["search"],
        notes="Created from upstream records.",
    )
    record = new_record(
        actor="agent-1",
        kind="decision",
        payload={"decision": {"action": "approve"}},
        provenance=provenance,
    )
    shared_data.write(record)

    fetched = shared_data.read(record.id)
    assert fetched is not None
    assert len(fetched.provenance.get("contributions", [])) == 1
    assert fetched.provenance["contributions"][0]["sources"] == ["r1", "r2"]


if __name__ == "__main__":
    main()
