"""Play Werewolf through a DOAgent session until one side is gone.

main loads the nine published roles, stores the session on disk, and calls the model.
The environment writes each game line on the outcome.
Each agent reads earlier outcome lines addressed to that player.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

import yaml

from doagent import Session
from examples._shared.llm_client import PROXY_BASE_URL, proxy_api_key
from experiments.multiagentbench.metrics import entropy
from experiments.multiagentbench.recover import (
    entropy_from_logs,
    mean_gap,
    modularity_of,
    vote_rounds,
    write_gap,
)
from experiments.multiagentbench.run_werewolf_service import SERVICE_MODEL
from experiments.multiagentbench.truth import read_truth, write_truth
from experiments.multiagentbench.werewolf_doagent import WerewolfEnv
from experiments.multiagentbench.werewolf_player import werewolf_policy
from experiments.multiagentbench.werewolf_session import lines_for

PUBLISHED_CONFIG = (
    Path(__file__).resolve().parent
    / "MARBLE"
    / "marble"
    / "configs"
    / "test_config"
    / "werewolf_config"
    / "werewolf_config.yaml"
)
NAME_POOL = (
    "Patricia",
    "Nicole",
    "Stephanie",
    "John",
    "David",
    "Mary",
    "Sandra",
    "Jami",
    "Priscilla",
)
OUTPUT_BASE = Path(__file__).resolve().parent / "werewolf_runs"


def assign_roles(seed: Optional[int] = None) -> Dict[str, str]:
    """Shuffle the nine published roles and assign a name to each.

    Args:
        seed: Optional shuffle seed.

    Returns:
        Player name to role.
    """
    document = yaml.safe_load(PUBLISHED_CONFIG.read_text(encoding="utf-8"))
    role_list = list(document["roles"])
    rng = random.Random(seed)
    if document.get("randomize_roles", True):
        rng.shuffle(role_list)
    names = list(NAME_POOL[: len(role_list)])
    if document.get("use_random_names", True):
        rng.shuffle(names)
    return {name: role for name, role in zip(names, role_list)}


def play(
    roles: Mapping[str, str],
    logging_level: int,
    complete: Callable[[list, list], Mapping[str, Any]],
    *,
    max_days: int = 1,
    shared_data: Optional[Mapping[str, Any]] = None,
    scenario_name: Optional[str] = None,
    output_base: Optional[str] = None,
    truth_path: Optional[Path] = None,
    on_step: Optional[Callable[[WerewolfEnv], None]] = None,
) -> Session:
    """Run until one side is gone, or until max_days is reached.

    Args:
        roles: Player id to role name.
        logging_level: 0, 1, or 2.
        complete: Model call used by each player.
        max_days: Stop after this many days even if both sides remain.
        shared_data: Session store. Defaults to memory.
        scenario_name: Run name used when the store is a file.
        output_base: Directory for a file store.
        truth_path: Truth file rewritten after each night and each day.
        on_step: Called after each environment step, once the truth file is current.

    Returns:
        The open session.
        The caller closes it.
    """
    env = WerewolfEnv(roles, max_days=max_days)
    config: Dict[str, Any] = {
            "shared_data": dict(shared_data or {"type": "memory"}),
            "run_config": {"logging_level": logging_level},
            "topology": {"mode": "peer_to_peer"},
            "policies": {
                player_id: werewolf_policy(
                    player_id,
                    lambda player_id=player_id: lines_for(
                        session.inspect("outcome"), player_id
                    ),
                    logging_level,
                    complete,
                )
                for player_id in roles
            },
    }
    if scenario_name:
        config["scenario_name"] = scenario_name
        config["output_base"] = output_base or str(OUTPUT_BASE)
    session = Session.from_config(config)
    wrapped = session.wrap_env(env, env_actor="werewolf_env")
    agents = session.create_agents(
        [
            {"id": player_id, "policy": {"name": player_id, "params": {}}}
            for player_id in roles
        ],
        goal="werewolf",
        payload_type="werewolf_action",
    )
    observations = wrapped.reset()
    round_id = 1
    while env.asked:
        actions = {}
        for player_id in list(env.asked):
            result = agents[player_id].decide(
                observations.get(player_id, {}),
                round_id,
            )
            actions[player_id] = result["action"]
        step = wrapped.step(actions)
        observations = step["observations"]
        if truth_path is not None:
            write_truth(
                truth_path,
                {"players": dict(roles), "phases": list(env.phases)},
            )
        if on_step is not None:
            on_step(env)
        round_id += 1
    return session


def write_run_artifacts(session: Session, roles: Mapping[str, str], directory: Path) -> None:
    """Write the truth file and the gaps from every session record.

    Args:
        session: Finished session.
        roles: Player id to role name.
        directory: Directory that receives truth.json and gap.json.
    """
    outcomes = session.inspect("outcome")
    updates = list(session.inspect("agent_update"))
    texts = {player_id: lines_for(outcomes, player_id) for player_id in roles}
    for record in updates:
        actor = getattr(record, "actor", None)
        if actor not in texts:
            continue
        texts[actor] = f"{texts[actor]}\n{json.dumps(record.payload, default=str)}"
    facts = []
    gaps = []
    population = len(roles)
    for outcome in outcomes:
        observations = outcome.payload.get("observations") or {}
        for line in observations.get("game_line") or []:
            content = str(line.get("content", ""))
            holders = list(line.get("recipients") or [])
            facts.append({"name": content, "holders": holders})
            recovered = entropy_from_logs(texts, content, population)
            if recovered is None:
                continue
            gaps.append(abs(entropy(len(holders), population) - recovered))
    directory.mkdir(parents=True, exist_ok=True)
    truth_path = directory / "truth.json"
    if not truth_path.is_file():
        write_truth(truth_path, {"players": dict(roles), "facts": facts})
    entropy_value = sum(gaps) / len(gaps) if gaps else None
    write_gap(
        directory / "gap.json",
        {"entropy": entropy_value, "modularity": _modularity_gap(truth_path, updates)},
    )


def _modularity_gap(truth_path: Path, updates: list) -> Optional[float]:
    """Return the exile-vote gap using agent updates and the truth phases.

    Args:
        truth_path: Truth file written while the game ran.
        updates: Agent update records from the session.

    Returns:
        The mean modularity distance.
        None when the truth file has no votes.
    """
    if not truth_path.is_file():
        return None
    document = read_truth(truth_path)
    day_votes = [phase["votes"] for phase in document.get("phases", []) if phase.get("votes")]
    if not day_votes:
        return None
    rounds = vote_rounds(updates)
    truth_scores = []
    recovered_scores: list[Optional[float]] = []
    for index, votes in enumerate(day_votes):
        truth_scores.append(modularity_of(votes))
        found = rounds[index] if index < len(rounds) else {}
        chosen = {name: found[name] for name in votes if name in found}
        if len(chosen) != len(votes):
            recovered_scores.append(None)
            continue
        recovered_scores.append(modularity_of(chosen))
    return mean_gap(truth_scores, recovered_scores)


def write_cost(
    directory: Path,
    wall_seconds: float,
    tokens: Optional[int],
) -> None:
    """Write storage, file count, tokens, and wall time for one run.

    Args:
        directory: Run directory to measure after the artifacts exist.
        wall_seconds: Seconds spent playing the game.
        tokens: Total model tokens for the run.
            None when the model call did not report usage.
    """
    directory.mkdir(parents=True, exist_ok=True)
    others = [
        item
        for item in directory.rglob("*")
        if item.is_file() and item.name != "cost.json"
    ]
    payload = {
        "storage_bytes": 0,
        "file_count": len(others) + 1,
        "tokens": tokens,
        "wall_seconds": wall_seconds,
    }
    encoded = json.dumps(payload, indent=2).encode("utf-8")
    payload["storage_bytes"] = sum(item.stat().st_size for item in others) + len(encoded)
    encoded = json.dumps(payload, indent=2).encode("utf-8")
    payload["storage_bytes"] = sum(item.stat().st_size for item in others) + len(encoded)
    (directory / "cost.json").write_text(encoded.decode("utf-8"), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    """Load nine roles, play on disk, and write the truth file, the gap, and the cost."""
    parser = argparse.ArgumentParser(description="DOAgent Werewolf")
    parser.add_argument("--logging-level", type=int, default=2, choices=(0, 1, 2))
    parser.add_argument("--max-days", type=int, default=10)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args(argv)
    roles = assign_roles(args.seed)
    latest = OUTPUT_BASE / "latest"
    usage = {"tokens": 0, "reported": False}

    def counted(messages: list, tools: list) -> Dict[str, Any]:
        raw = call_model(messages, tools)
        if raw.get("tokens") is not None:
            usage["tokens"] += int(raw["tokens"])
            usage["reported"] = True
        return raw

    started = time.perf_counter()
    session = play(
        roles,
        args.logging_level,
        counted,
        max_days=args.max_days,
        shared_data={"type": "file"},
        scenario_name="werewolf_doagent",
        output_base=str(OUTPUT_BASE),
        truth_path=latest / "truth.json",
    )
    wall_seconds = time.perf_counter() - started
    try:
        write_run_artifacts(session, roles, latest)
        write_cost(
            OUTPUT_BASE,
            wall_seconds,
            usage["tokens"] if usage["reported"] else None,
        )
    finally:
        session.close()


def call_model(messages: list, tools: list) -> Dict[str, Any]:
    """Call the university model with the published tools.

    Args:
        messages: System and user messages.
        tools: Tool schemas from the published prompt file.

    Returns:
        The tool arguments, and the message text as the explanation.
    """
    from openai import OpenAI

    client = OpenAI(api_key=proxy_api_key(), base_url=PROXY_BASE_URL)
    response = client.chat.completions.create(
        model=SERVICE_MODEL,
        messages=messages,
        tools=tools,
        tool_choice="required",
    )
    message = response.choices[0].message
    arguments: Dict[str, Any] = {}
    if message.tool_calls:
        arguments = json.loads(message.tool_calls[0].function.arguments)
    total = None
    if response.usage is not None:
        total = response.usage.total_tokens
    return {"action": arguments, "explanation": message.content or "", "tokens": total}


if __name__ == "__main__":
    main()
