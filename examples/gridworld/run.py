"""Canonical command-line entry point for the gridworld example."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
from typing import Any, Dict

from doagent import Session, RunReporter, make_env
from doagent.analysis import (
    accountability,
    interpretability,
    provenance,
    traceability,
)
from examples._shared.llm_client import create_llm_tool
from examples.gridworld.env import create_gridworld_env
from examples.gridworld.session import (
    load_config,
    make_session_config,
    parse_agent_configs,
    parse_topology,
    run_with_session,
)


def main() -> None:
    """Run one gridworld example from YAML and write analysis artefacts."""
    script_dir = Path(__file__).resolve().parent
    default_config = script_dir / "config.yaml"
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_config
    config = load_config(config_path)

    run_cfg = config.get("run", {})
    scenario = config.get("scenario", {})
    env_cfg = scenario.get("env", {})
    participation_cfg = scenario.get("participation", {}) or {}
    storage_type = str(scenario.get("storage", "file")).lower()
    mongo_uri = scenario.get("mongo_uri") or "mongodb://localhost:27017"

    rounds = int(run_cfg.get("rounds", 10))
    seed = int(run_cfg.get("seed", 0))
    render = bool(scenario.get("render", False))
    render_mode = scenario.get("render_mode")
    if render and render_mode is None:
        render_mode = "ansi"
    render_delay = float(scenario.get("render_delay", 0.3 if render_mode == "human" else 0.0))
    print_every = int(scenario.get("print_every", 0))
    landmarks_total = int(env_cfg["landmarks"]) if "landmarks" in env_cfg else None

    energy_model = bool(participation_cfg.get("energy_model", False))
    energy_min = int(participation_cfg.get("energy_min", 6))
    energy_max = int(participation_cfg.get("energy_max", 12))
    energy_decay = int(participation_cfg.get("energy_decay", 1))
    energy_recharge = int(participation_cfg.get("energy_recharge", 1))
    energy_leave_threshold = int(participation_cfg.get("energy_leave_threshold", 2))

    agent_configs = parse_agent_configs(config)
    agent_ids = [c["id"] for c in agent_configs]
    topology_mode, visibility = parse_topology(config)
    hub_id = "hub"

    needs_llm = any(c["policy"]["name"] == "grid_llm" for c in agent_configs)
    if needs_llm:
        llm_tool = create_llm_tool()
        for c in agent_configs:
            if c["policy"]["name"] == "grid_llm":
                c.setdefault("tools", {})["llm"] = llm_tool

    env = make_env(
        create_gridworld_env,
        width=int(env_cfg.get("width", 6)),
        height=int(env_cfg.get("height", 6)),
        agent_ids=agent_ids,
        landmarks=int(env_cfg.get("landmarks", 2)),
        observation_radius=int(env_cfg.get("observation_radius", 1)),
        max_cycles=int(env_cfg.get("max_cycles", 25)),
        seed=run_cfg.get("seed"),
        render_mode=render_mode,
    )

    run_kwargs: Dict[str, Any] = dict(
        env=env,
        configs=agent_configs,
        rounds=rounds,
        seed=seed,
        energy_model=energy_model,
        energy_min=energy_min,
        energy_max=energy_max,
        energy_decay=energy_decay,
        energy_recharge=energy_recharge,
        energy_leave_threshold=energy_leave_threshold,
        landmarks_total=landmarks_total,
        render=render,
        render_delay=render_delay,
        print_every=print_every,
    )
    output_base = "output"

    print("\n=== Grid-world run ===")
    session = Session.from_config(
        make_session_config(
            shared_data_type=storage_type,
            shared_data_uri=mongo_uri if storage_type == "mongo" else None,
            scenario_name="gridworld",
            output_base=output_base,
            topology_mode=topology_mode,
            visibility=visibility,
            hub_id=hub_id,
            participation=energy_model,
        )
    )
    run_path = Path(session.run_path)
    reporter = RunReporter(
        "gridworld", print_every=print_every,
        record_series=True, series_every=1, record_entropy=True, action_space=5,
    )
    summary = run_with_session(session, **run_kwargs, reporter=reporter)
    reporter.finalize(
        rounds=rounds, seed=seed, outcomes=summary["outcomes"],
        elapsed_seconds=0.0, output_bytes=0, render=render,
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
            attr = accountability.causal_attribution(run_id, output_base=output_base, write_output=True)
            print(f"Accountability: wrote analysis/accountability/ ({len(attr.get('agents', []))} agents)")
        except Exception as e:
            print(f"  Accountability: {e}")
        try:
            last_id = effective_id or "last"
            units = interpretability.build_atomic_explanations(last_id, run_id, output_base=output_base, write_output=True)
            print(f"Interpretability: wrote analysis/interpretability/ ({len(units)} atomic explanation units)")
            if units:
                levels = Counter(u.get("level") for u in units)
                print(f"  Levels: {dict(levels)}")
                for idx, unit in enumerate(units[:8], start=1):
                    print(f"  {idx:02d}. {unit.get('rendered_text', '(missing rendered_text)')}")
        except Exception as e:
            print(f"  Interpretability: {e}")
    print(f"\nRun output: {run_path} (run_id={run_id})")


if __name__ == "__main__":
    main()
