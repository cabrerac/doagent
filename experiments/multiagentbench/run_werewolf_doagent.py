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
from experiments.multiagentbench.cost import (
    cl100k_encode,
    doagent_record_paths,
    explanation_overhead,
    token_levels,
    user_text,
    write_cost,
)
from experiments.multiagentbench.metrics import entropy
from experiments.multiagentbench.recover import (
    entropy_from_logs,
    mean_gap,
    modularity_of,
    vote_rounds,
    write_gap,
)
from experiments.multiagentbench.run_werewolf_service import (
    SERVICE_MODEL,
    call_with_retry,
    install_timestamps,
    restore_timestamps,
)
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


def prepare_game_dir(path: Optional[str], default: Path) -> Path:
    """Create the folder that will hold one game.

    Args:
        path: Folder chosen by the caller.
            None uses default.
        default: Folder used when path is omitted.

    Returns:
        The absolute game folder.
    """
    folder = Path(path).resolve() if path else default.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    return folder


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


def keep_going(label: str, operation: Callable[[], Any]) -> None:
    """Run one finishing step.

    A failure is printed.
    The exception is not raised.

    Args:
        label: Name of the step, used in the log line.
        operation: The score or cost write.
    """
    try:
        operation()
    except Exception as exc:
        print(f"{label} failed: {exc}", flush=True)


def main(argv: list[str] | None = None) -> None:
    """Load nine roles, play on disk, and write the truth file, the gap, and the cost."""
    parser = argparse.ArgumentParser(description="DOAgent Werewolf")
    parser.add_argument("--logging-level", type=int, default=2, choices=(0, 1, 2))
    parser.add_argument("--max-days", type=int, default=10)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--model", default=SERVICE_MODEL)
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    roles = assign_roles(args.seed)
    output = prepare_game_dir(args.output, OUTPUT_BASE / "doagent")
    print(f"DOAgent game directory: {output}", flush=True)
    usage = {"tokens": 0, "reported": False}
    prompts: list[tuple[str, str]] = []
    originals = install_timestamps()
    started = time.perf_counter()
    client = None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=proxy_api_key(), base_url=PROXY_BASE_URL)

        def counted(messages: list, tools: list) -> Dict[str, Any]:
            raw = call_model(messages, tools, args.model, client)
            if raw.get("tokens") is not None:
                usage["tokens"] += int(raw["tokens"])
                usage["reported"] = True
            if args.logging_level >= 2:
                explanation = raw.get("explanation")
                if not isinstance(explanation, str):
                    explanation = ""
                prompts.append((user_text(messages), explanation))
            return raw

        try:
            session = play(
                roles,
                args.logging_level,
                counted,
                max_days=args.max_days,
                shared_data={"type": "file"},
                scenario_name="werewolf_doagent",
                output_base=str(output),
                truth_path=output / "truth.json",
            )
        except Exception as exc:
            print(f"DOAgent game failed: {type(exc).__name__}: {exc}", flush=True)
            raise
        print(f"DOAgent records: {session.run_path}", flush=True)
        wall_seconds = time.perf_counter() - started
        record_paths = doagent_record_paths(session.run_path)
        try:
            keep_going(
                "Gap scoring",
                lambda: write_run_artifacts(session, roles, output),
            )
        finally:
            session.close()
        def score_cost() -> None:
            tokens = usage["tokens"] if usage["reported"] else None
            levels = None
            if args.logging_level >= 2 and tokens is not None:
                try:
                    overhead = 0
                    for user, explanation in prompts:
                        overhead += explanation_overhead(user, explanation, cl100k_encode)
                    levels = token_levels(tokens, overhead)
                except Exception as exc:
                    print(f"Token projection failed: {exc}", flush=True)
            write_cost(output, wall_seconds, tokens, record_paths, levels)

        keep_going("Cost scoring", score_cost)
        print(f"DOAgent game finished. Scores in {output}.", flush=True)
    finally:
        try:
            if client is not None:
                client.close()
        finally:
            restore_timestamps(originals)


def log_model_request(messages: list, tools: list, kind: str, detail: str) -> None:
    """Print the user prompt sent for one model reply.

    Args:
        messages: System and user messages that were sent.
        tools: Tool schemas sent with the request.
        kind: Kept or Rejected.
        detail: Elapsed seconds, or why the reply was rejected.
    """
    name = ""
    if tools:
        name = str(tools[0].get("function", {}).get("name", ""))
    user = ""
    for message in messages:
        if message.get("role") == "user":
            user = str(message.get("content", ""))
    print(f"{kind} model request. Tool {name}. {detail}", flush=True)
    print(user, flush=True)


def generation_call(
    operation: Callable[[], Any],
    pause: Callable[[float], None] = time.sleep,
) -> Any:
    """Call operation up to four times.

    Wait five seconds after each failure.

    Args:
        operation: One model completion.
        pause: Wait function used after a failure.

    Returns:
        The value returned by operation.

    Raises:
        Exception: Chat Completion failed too many times.
    """
    rounds = 0
    while True:
        rounds += 1
        try:
            return operation()
        except Exception as exc:
            print(f"Chat Generation Error: {exc}", flush=True)
            pause(5)
            if rounds > 3:
                raise Exception("Chat Completion failed too many times") from exc


def reply_action(message: Any) -> Optional[Dict[str, Any]]:
    """Return the tool arguments from one model message.

    Args:
        message: The first choice message from the model.

    Returns:
        The parsed tool arguments.
        None when the message has no tool call or the arguments are not JSON.
    """
    tool_calls = getattr(message, "tool_calls", None)
    if not tool_calls:
        return None
    try:
        parsed = json.loads(tool_calls[0].function.arguments)
    except (json.JSONDecodeError, TypeError, AttributeError, IndexError, KeyError):
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def unused_reply(tokens: Optional[int] = None) -> Dict[str, Any]:
    """Return the action used when a model reply cannot be applied.

    Args:
        tokens: Token count from the reply, when the model reported one.

    Returns:
        An action of no_action and an empty explanation.
    """
    return {
        "action": "no_action",
        "target": None,
        "explanation": "",
        "tokens": tokens,
    }


def call_model(
    messages: list,
    tools: list,
    model: str = SERVICE_MODEL,
    client: Any = None,
) -> Dict[str, Any]:
    """Call the university model with the published tools.

    A call that throws is tried four times, five seconds apart.
    That whole attempt is tried again, up to five times.
    The call uses temperature 0.7.
    A reply with no tool call, or arguments that are not JSON, is no_action.
    The same result is used when every attempt throws.
    A client passed in is reused and left open.
    A client this function opens is closed before it returns.

    Args:
        messages: System and user messages.
        tools: Tool schemas from the published prompt file.
        model: Model name sent to the proxy.
        client: Open client reused for this call.
            A new client is opened when this is omitted.

    Returns:
        The tool arguments, and the message text as the explanation.
        When the reply cannot be used, action is the text no_action.
    """
    owns_client = client is None
    if client is None:
        from openai import OpenAI

        client = OpenAI(api_key=proxy_api_key(), base_url=PROXY_BASE_URL)
    print("Model call started.", flush=True)
    started = time.perf_counter()
    arguments: Optional[Dict[str, Any]] = None
    total: Optional[int] = None
    message: Any = None

    def once() -> Any:
        return generation_call(
            lambda: client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="required",
                temperature=0.7,
            )
        )

    try:
        response = call_with_retry(once)
        message = response.choices[0].message
        arguments = reply_action(message)
        if response.usage is not None:
            total = response.usage.total_tokens
    except Exception as exc:
        log_model_request(messages, tools, "Rejected", str(exc))
        return unused_reply()
    finally:
        elapsed = time.perf_counter() - started
        print(f"Model call finished in {elapsed:.1f}s.", flush=True)
        if owns_client:
            client.close()
    if arguments is None:
        log_model_request(messages, tools, "Rejected", "model reply had no tool call")
        return unused_reply(total)
    log_model_request(messages, tools, "Kept", f"{elapsed:.1f}s")
    return {
        "action": arguments,
        "explanation": getattr(message, "content", None) or "",
        "tokens": total,
    }


if __name__ == "__main__":
    main()
