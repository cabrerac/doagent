"""Canonical command-line entry point for the push example."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any, Dict

from doagent import Session, RunReporter, make_env
from doagent.analysis import interpretability, provenance, traceability
from examples._shared.llm_client import create_llm_tool
from examples.push.env import create_push_env
from examples.push.policies import (
    heuristic_goal_seek,
    heuristic_push_block,
    make_agent_configs,
    push_llm_policy_factory,
)
from examples.push.session import run_with_session


def main() -> None:
    """Run one push example and optionally a second LLM comparison run."""
    parser = argparse.ArgumentParser(description="Push example")
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
            env_params["render_mode"] = "human"
        env = make_env(create_push_env, **env_params)
    except ImportError as exc:
        raise SystemExit(
            "PettingZoo is required for this example. Install with: pip install pettingzoo"
        ) from exc

    configs = make_agent_configs()
    output_base = "./output"

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
                "push_llm": push_llm_policy_factory,
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
                "policy": {"name": "push_llm", "params": {"model": "gpt-4o", "confidence_threshold": 0.3}},
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
