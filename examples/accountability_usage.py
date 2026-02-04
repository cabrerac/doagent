"""Accountability helper example."""

from doagent.core import InMemorySharedData, new_record
from doagent.records import new_accountability


def main() -> None:
    shared_data = InMemorySharedData()

    accountability = new_accountability(
        owner="team-a",
        policy_id="policy-001",
        responsibility_scope="decisions",
    )
    record = new_record(
        actor="agent-1",
        kind="decision",
        payload={"decision": {"action": "approve"}},
        accountability=accountability,
    )
    shared_data.write(record)

    fetched = shared_data.read(record.id)
    assert fetched is not None
    assert fetched.accountability["owner"] == "team-a"
    assert fetched.accountability["policy_id"] == "policy-001"
    assert fetched.accountability["responsibility_scope"] == "decisions"


if __name__ == "__main__":
    main()
