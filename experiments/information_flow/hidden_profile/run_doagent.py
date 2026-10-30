"""Run Hidden Profile through a DOAgent session."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from doagent import Session

from experiments.information_flow.hidden_profile.policies import scripted_policy
from experiments.information_flow.hidden_profile.rules import (
    DEFAULT_CONFIG,
    HiddenProfileConfig,
    HiddenProfileRules,
)

OUTPUT_BASE = Path(__file__).resolve().parent / "hidden_profile_runs"
RECORD_KINDS = ("outcome", "agent_update", "trace")


@dataclass(frozen=True)
class SessionRun:
    """Point at the rules and the exported session records.

    Args:
        rules: Rules object that played the episode.
        records_path: Path of the exported record file.
    """

    rules: HiddenProfileRules
    records_path: Path


def run_session(
    seed: int,
    logging_level: int = 1,
    output_base: str | Path | None = None,
    config: HiddenProfileConfig = DEFAULT_CONFIG,
    allocation: Mapping[str, Sequence[str]] | None = None,
) -> SessionRun:
    """Play one episode through a peer-to-peer session.

    Args:
        seed: Integer seed for the private-fact deal.
        logging_level: Session logging level, 0, 1, or 2.
        output_base: Directory for the session store and the record export.
        config: Hidden profile configuration.
        allocation: Optional private-fact ids already assigned to each agent.
            When provided, the seed only labels the episode.

    Returns:
        The rules that played, and the path of the exported records.

    Raises:
        ValueError: The logging level is not 0, 1, or 2.
        RuntimeError: The episode did not reach a vote.
    """
    if isinstance(logging_level, bool) or logging_level not in (0, 1, 2):
        raise ValueError("logging_level must be 0, 1, or 2")
    folder = Path(output_base) if output_base is not None else OUTPUT_BASE
    folder.mkdir(parents=True, exist_ok=True)
    rules = HiddenProfileRules(config)
    session_config = {
        "shared_data": {"type": "file"},
        "run_config": {"logging_level": logging_level},
        "topology": {"mode": "peer_to_peer"},
        "policies": {
            agent_id: _policy_factory(agent_id)
            for agent_id in rules.agents
        },
        "scenario_name": "hidden_profile_doagent",
        "output_base": str(folder),
    }
    session = Session.from_config(session_config)
    try:
        wrapped = session.wrap_env(rules, env_actor="hidden_profile_env")
        agents = session.create_agents(
            [
                {"id": agent_id, "policy": {"name": agent_id, "params": {}}}
                for agent_id in rules.agents
            ],
            goal="hidden_profile",
            payload_type="hidden_profile_action",
        )
        observations = wrapped.reset(seed=seed, allocation=allocation)
        finished = False
        for round_id in range(1, config.horizon + 2):
            actions = {
                agent_id: agent.decide(
                    observations[agent_id],
                    round_id,
                    inputs={"observation": observations[agent_id]},
                )["action"]
                for agent_id, agent in agents.items()
            }
            step = wrapped.step(actions)
            observations = step["observations"]
            if all(step["done"].values()):
                finished = True
                break
        if not finished:
            raise RuntimeError("the episode did not reach a vote")
        records = {
            kind: [asdict(record) for record in session.inspect(kind)]
            for kind in RECORD_KINDS
        }
    finally:
        session.close()
    records_path = folder / "records.json"
    records_path.write_text(
        json.dumps(records, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return SessionRun(rules=rules, records_path=records_path)


def comparable_session(records: Mapping[str, Sequence[Mapping[str, object]]]) -> dict[str, list[object]]:
    """Return session records with the library id and clock removed.

    A link that names a record is rewritten to that record's place in the file.

    Args:
        records: Exported session records, one list per kind.

    Returns:
        The same records without ids or clocks.
    """
    places: dict[str, str] = {}
    for kind, rows in records.items():
        for index, row in enumerate(rows):
            record_id = row.get("id")
            if isinstance(record_id, str):
                places[record_id] = f"{kind}:{index}"

    def walk(value: object) -> object:
        if isinstance(value, str):
            return places.get(value, value)
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, dict):
            return {
                key: walk(item)
                for key, item in value.items()
                if key not in ("id", "timestamp")
            }
        return value

    return {kind: [walk(row) for row in rows] for kind, rows in records.items()}


def _policy_factory(agent_id: str) -> Callable[[Mapping[str, object]], Callable]:
    """Return a session factory for one scripted policy.

    Args:
        agent_id: Identifier of the agent that will use the policy.

    Returns:
        A factory that ignores parameters and returns the policy.
    """
    policy = scripted_policy(agent_id)

    def factory(params: Mapping[str, object]) -> Callable:
        """Return the scripted policy."""
        del params
        return policy

    return factory


def main() -> None:
    """Run one session from the command line."""
    parser = argparse.ArgumentParser(description="Run Hidden Profile in a DOAgent session.")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--logging-level", type=int, default=1)
    parser.add_argument("--output-base", type=Path, default=OUTPUT_BASE)
    args = parser.parse_args()
    result = run_session(args.seed, args.logging_level, args.output_base)
    print(result.records_path)


if __name__ == "__main__":
    main()
