"""Interpretability records example."""

from doagent.core import InMemorySharedData, new_explanation_record, new_record


def main() -> None:
    shared_data = InMemorySharedData()

    decision = new_record(
        actor="agent-1",
        kind="decision",
        payload={"decision": {"action": "approve"}},
    )
    shared_data.write(decision)

    explanation = new_explanation_record(
        actor="agent-1",
        decision_id=decision.id,
        summary="Approved due to policy compliance.",
        details="The request met all mandatory checks.",
        evidence=["policy-1"],
    )
    shared_data.write(explanation)

    record = list(shared_data.listen("explanation"))[0]
    assert record.payload["decision_id"] == decision.id


if __name__ == "__main__":
    main()
