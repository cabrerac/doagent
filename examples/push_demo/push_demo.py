"""Push demo using the DOAgent Session API.

Demonstrates config-driven library usage with a PettingZoo environment.
No doagent.core or doagent.records imports needed.
"""

from __future__ import annotations

import json
from pathlib import Path
import random
from typing import Any, Dict

from doagent import Session, RunReporter, make_env
from doagent.analysis import interpretability, provenance, traceability
from examples.push_demo.env import create_push_env


# ---------------------------------------------------------------------------
# Policy factories (callable entry points for config-driven registration)
# ---------------------------------------------------------------------------

def _action_from_vector(dx: float, dy: float) -> int:
    if abs(dx) < 1e-6 and abs(dy) < 1e-3:
        return 0
    if abs(dx) >= abs(dy):
        return 2 if dx > 0 else 1
    return 4 if dy > 0 else 3


def _epsilon_greedy(base: int, epsilon: float, rng: random.Random) -> int:
    return rng.choice([0, 1, 2, 3, 4]) if rng.random() < epsilon else base


def fixed_policy(params: Dict[str, Any]) -> Any:
    action = params.get("action", 0)
    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        return {"decision": {"action": action}}
    return decide


def heuristic_goal_seek(params: Dict[str, Any]) -> Any:
    epsilon = float(params.get("epsilon", 0.0))
    rng = random.Random(params.get("seed", 0))
    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        obs = request.get("inputs", {}).get("observation", [])
        dx, dy = (float(obs[2]), float(obs[3])) if len(obs) >= 4 else (0.0, 0.0)
        return {"decision": {"action": _epsilon_greedy(_action_from_vector(dx, dy), epsilon, rng)}}
    return decide


def heuristic_push_block(params: Dict[str, Any]) -> Any:
    epsilon = float(params.get("epsilon", 0.0))
    rng = random.Random(params.get("seed", 0))
    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        obs = request.get("inputs", {}).get("observation", [])
        dx, dy = (float(obs[6]), float(obs[7])) if len(obs) >= 8 else (0.0, 0.0)
        return {"decision": {"action": _epsilon_greedy(_action_from_vector(dx, dy), epsilon, rng)}}
    return decide


# ---------------------------------------------------------------------------
# Agent configs
# ---------------------------------------------------------------------------

def make_agent_configs() -> list[Dict[str, Any]]:
    """Agent configs as plain dicts: id, policy, metadata."""
    return [
        {
            "id": "adversary_0",
            "policy": {"name": "heuristic_push_block", "params": {"epsilon": 0.2, "seed": 1}},
            "metadata": {"explanation": "Heuristic push/block with epsilon-greedy exploration."},
        },
        {
            "id": "agent_0",
            "policy": {"name": "heuristic_goal_seek", "params": {"epsilon": 0.2, "seed": 2}},
            "metadata": {"explanation": "Heuristic goal-seek with epsilon-greedy exploration."},
        },
    ]


# ---------------------------------------------------------------------------
# Session-based run (config-driven)
# ---------------------------------------------------------------------------

def run_with_session(
    session: Session,
    env: Any,
    configs: list[Dict[str, Any]],
    rounds: int,
    seed: int,
    *,
    render: bool = False,
    reporter: RunReporter | None = None,
) -> int:
    """Run push scenario using the DOAgent Session API. Returns outcome count."""
    wrapped_env = session.wrap_env(env, env_actor="push_env")
    agents = session.create_agents(
        configs, goal="push_towards_landmark",
    )

    observations = wrapped_env.reset(seed=seed)
    if render:
        wrapped_env.render()

    outcome_count = 0
    for round_id in range(1, rounds + 1):
        actions: Dict[str, Any] = {}
        for agent_id, agent in agents.items():
            result = agent.decide(observations.get(agent_id, {}), round_id)
            actions[agent_id] = result["action"]

        step = wrapped_env.step(actions)
        if reporter is not None:
            reporter.on_outcome(round_id, actions, step["rewards"])
        if render:
            wrapped_env.render()
        observations = step["observations"]
        outcome_count += 1

    return outcome_count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    rounds = 100
    seed = 123
    render_demo = True
    print_every = 10

    try:
        env_params: Dict[str, Any] = {
            "max_cycles": rounds,
            "continuous_actions": False,
            "dynamic_rescaling": False,
        }
        if render_demo:
            env_params["render_mode"] = render_demo
        env = make_env(create_push_env, **env_params)
    except ImportError as exc:
        raise SystemExit(
            "PettingZoo is required for this example. Install with: pip install pettingzoo"
        ) from exc

    configs = make_agent_configs()

    # -- Single file run (library creates run_id, output folder, records/, metadata.json) --
    print("\n=== Push run (file-backed) ===")
    session = Session.from_config({
        "shared_data": {"type": "file"},
        "scenario_name": "push",
        "output_base": "./output",
        "run_config": {"logging_level": 2},
        "policies": {
            "fixed": fixed_policy,
            "heuristic_goal_seek": heuristic_goal_seek,
            "heuristic_push_block": heuristic_push_block,
        },
    })
    run_path = Path(session.run_path)
    reporter = RunReporter(
        "push", print_every=print_every,
        record_series=True, series_every=1, record_entropy=True, action_space=5,
    )
    outcomes = run_with_session(
        session, env, configs, rounds, seed,
        render=render_demo, reporter=reporter,
    )
    reporter.finalize(
        rounds=rounds, seed=seed, outcomes=outcomes,
        elapsed_seconds=0.0, output_bytes=0, render=render_demo,
        path=str(run_path / "records"),
    )

    # -- Analysis showcase: use only the analyses that fit this scenario --
    # Push has no "discovery" semantics, so we skip causal attribution; provenance, traceability, interpretability apply.
    output_base = "./output"
    run_id = session.run_id
    chain = None
    if run_id:
        print(f"\n=== Analysis (run_id={run_id}) ===")
        try:
            chain = provenance.walk_chain("last", run_id, output_base=output_base, max_depth=6)
            print(f"Provenance: chain root {chain.get('record_id', '?')}, {len(chain.get('children', []))} direct links")
            provenance.render_chain_tree("last", run_id, str(run_path / "provenance_tree.png"), output_base=output_base)
            print(f"  -> {run_path / 'provenance_tree.png'}")
        except Exception as e:
            print(f"  Provenance: {e}")
        try:
            G = traceability.build_trace_graph(run_id, output_base=output_base)
            print(f"Traceability: graph {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
            traceability.render_trace_graph(G, str(run_path / "trace_graph.png"))
            print(f"  -> {run_path / 'trace_graph.png'}")
        except Exception as e:
            print(f"  Traceability: {e}")
        try:
            last_id = chain.get("record_id") if chain else None
            if last_id:
                explanations = interpretability.get_explanations_for(last_id, run_id, output_base=output_base)
                print(f"Interpretability: {len(explanations)} explanation/decision records for last outcome")
                if explanations:
                    out_file = run_path / "explanations_for_last.json"
                    with out_file.open("w", encoding="utf-8") as f:
                        json.dump(explanations, f, indent=2, default=str)
                    print(f"  -> {out_file}")
                    for ex in explanations[:5]:
                        print(f"    - {ex.get('kind', '?')} {str(ex.get('id', ''))[:12]}... (actor: {ex.get('actor', '?')})")
                    if len(explanations) > 5:
                        print(f"    ... and {len(explanations) - 5} more")
        except Exception as e:
            print(f"  Interpretability: {e}")
    print(f"\nRun output: {run_path} (run_id={run_id})")


if __name__ == "__main__":
    main()
