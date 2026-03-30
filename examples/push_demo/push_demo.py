"""
Push demo using the DOAgent Session API.
Demonstrates config-driven library usage with a PettingZoo environment.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import random
from typing import Any, Dict

from doagent import Session, RunReporter, make_env
from doagent.analysis import interpretability, provenance, traceability
from examples.push_demo.env import create_push_env
from examples.llm_policy import create_llm_tool, llm_decide_factory


# ---------------------------------------------------------------------------
# Policy factories
# ---------------------------------------------------------------------------

def _action_from_vector(dx: float, dy: float) -> int:
    if abs(dx) < 1e-6 and abs(dy) < 1e-3:
        return 0
    if abs(dx) >= abs(dy):
        return 2 if dx > 0 else 1
    return 4 if dy > 0 else 3


def _epsilon_greedy(base: int, epsilon: float, rng: random.Random) -> int:
    return rng.choice([0, 1, 2, 3, 4]) if rng.random() < epsilon else base


def heuristic_goal_seek(params: Dict[str, Any]) -> Any:
    epsilon = float(params.get("epsilon", 0.0))
    rng = random.Random(params.get("seed", 0))
    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        obs = request.get("inputs", {}).get("observation", [])
        dx, dy = (float(obs[2]), float(obs[3])) if len(obs) >= 4 else (0.0, 0.0)
        return {"choice": {"status": "act", "action": _epsilon_greedy(_action_from_vector(dx, dy), epsilon, rng)}}
    return decide


def heuristic_push_block(params: Dict[str, Any]) -> Any:
    epsilon = float(params.get("epsilon", 0.0))
    rng = random.Random(params.get("seed", 0))
    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        obs = request.get("inputs", {}).get("observation", [])
        dx, dy = (float(obs[6]), float(obs[7])) if len(obs) >= 8 else (0.0, 0.0)
        return {"choice": {"status": "act", "action": _epsilon_greedy(_action_from_vector(dx, dy), epsilon, rng)}}
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
# Run environment with DOAgent Session API
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
            action = result["action"]
            actions[agent_id] = action if action is not None else 0

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

def _push_llm_policy_factory(params: Dict[str, Any]) -> Any:
    """LLM policy factory specialised for the push environment."""
    merged = {
        "action_space": {0: "noop", 1: "left", 2: "right", 3: "down", 4: "up"},
        "confidence_threshold": 0.3,
        **params,
    }
    return llm_decide_factory(merged)


def main() -> None:
    parser = argparse.ArgumentParser(description="Push demo")
    parser.add_argument("--llm", action="store_true", help="Run an additional LLM comparison after the heuristic run.")
    parser.add_argument("--no-render", action="store_true", help="Disable environment rendering.")
    args = parser.parse_args()

    rounds = 100
    seed = 123
    render_demo = not args.no_render
    print_every = 10

    try:
        env_params: Dict[str, Any] = {
            "max_cycles": rounds,
            "continuous_actions": False,
            "dynamic_rescaling": False,
        }
        if render_demo:
            env_params["render_mode"] = "human"  # PettingZoo expects "human" for a visible window
        env = make_env(create_push_env, **env_params)
    except ImportError as exc:
        raise SystemExit(
            "PettingZoo is required for this example. Install with: pip install pettingzoo"
        ) from exc

    configs = make_agent_configs()
    output_base = "./output"

    # -- Single file run (library creates run_id, output folder, records/, metadata.json) --
    print("\n=== Push run (file-backed) ===")
    session = Session.from_config({
        "shared_data": {"type": "file"},
        "scenario_name": "push",
        "output_base": output_base,
        "run_config": {"logging_level": 2},
        "policies": {
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

    # -- Analysis: write_output=True writes to output_base/run_id/analysis/<category>/ --
    run_id = session.run_id
    if run_id:
        print(f"\n=== Analysis (run_id={run_id}) ===")
        effective_id = None
        try:
            effective_id = provenance.render_chain_tree("last", run_id, output_base=output_base, write_output=True)
            print("Provenance: wrote analysis/provenance/ (provenance_tree.png, .pdf)")
        except Exception as e:
            print(f"  Provenance: {e}")
        try:
            G = traceability.build_trace_graph(run_id, output_base=output_base, write_output=True)
            print(f"Traceability: wrote analysis/traceability/ ({G.number_of_nodes()} nodes, {G.number_of_edges()} edges)")
        except Exception as e:
            print(f"  Traceability: {e}")
        try:
            # Use same outcome id as provenance so explanations refer to the same outcome.
            last_id = effective_id or "last"
            units = interpretability.build_atomic_explanations(last_id, run_id, output_base=output_base, write_output=True)
            print(f"Interpretability: wrote analysis/interpretability/ ({len(units)} atomic explanation units)")
            if units:
                levels = Counter(u.get("level") for u in units)
                print(f"  Levels: {dict(levels)}")
                for idx, unit in enumerate(units[:5], start=1):
                    print(f"  {idx:02d}. {unit.get('rendered_text', '(missing rendered_text)')}")
        except Exception as e:
            print(f"  Interpretability: {e}")
    print(f"\nRun output: {run_path} (run_id={run_id})")

    # -- Optional LLM comparison run --
    if args.llm:
        print("\n=== LLM comparison run ===")
        try:
            llm_tool = create_llm_tool()
        except RuntimeError as exc:
            print(f"Skipping LLM run: {exc}")
            return

        llm_env = make_env(create_push_env, max_cycles=rounds, continuous_actions=False, dynamic_rescaling=False)
        llm_session = Session.from_config({
            "shared_data": {"type": "file"},
            "scenario_name": "push_llm",
            "output_base": output_base,
            "run_config": {"logging_level": 2},
            "policies": {
                "heuristic_push_block": heuristic_push_block,
                "push_llm": _push_llm_policy_factory,
            },
        })
        llm_configs = [
            {
                "id": "adversary_0",
                "policy": {"name": "heuristic_push_block", "params": {"epsilon": 0.2, "seed": 1}},
                "metadata": {"explanation": "Heuristic push/block with epsilon-greedy exploration."},
            },
            {
                "id": "agent_0",
                "policy": {"name": "push_llm", "params": {"model": "gemini-2.5-flash", "confidence_threshold": 0.3}},
                "tools": {"llm": llm_tool},
                "metadata": {"explanation": "LLM-based goal-seek policy."},
            },
        ]
        llm_outcomes = run_with_session(
            llm_session, llm_env, llm_configs, rounds, seed,
            render=False,
        )
        llm_updates = llm_session.inspect("agent_update")
        abstain_count = sum(
            1 for r in llm_updates
            if r.payload.get("decision", {}).get("response", {}).get("choice", {}).get("status") == "abstain"
        )
        print(f"LLM run completed ({llm_outcomes} rounds, {abstain_count} abstentions).")
        print(f"LLM run id: {llm_session.run_id}")


if __name__ == "__main__":
    main()
