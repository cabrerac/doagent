"""Topology comparison experiment: run gridworld under centralised, peer_to_peer, and federated topologies.

Uses doagent.analysis to build trace graphs and causal attribution per run.
Run from repository root:
  python -m experiments.run_topology_comparison [--output-dir output/topo_comparison]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from doagent import Session, make_env
from doagent.analysis import accountability, traceability
from examples.gridworld_demo.gridworld_demo import (
    GRIDWORLD_POLICIES,
    _make_session_config,
    load_config,
    parse_agent_configs,
    parse_topology,
    run_with_session,
)
from examples.gridworld_demo.env import create_gridworld_env

TOPOLOGIES = [
    ("centralised", "centralised", None),
    ("peer_to_peer", "peer_to_peer", {"agent_0": ["agent_1"], "agent_1": ["agent_2"], "agent_2": ["agent_3"], "agent_3": ["agent_0"]}),
    ("federated", "federated", None),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run gridworld under 3 topologies and compare via analysis.")
    parser.add_argument("--output-dir", default="output/topo_comparison", help="Directory for comparison outputs")
    parser.add_argument("--config", default=None, help="Path to gridworld config YAML (optional)")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent.parent
    default_config = script_dir / "examples" / "gridworld_demo" / "gridworld_demo_config.yaml"
    config_path = Path(args.config) if args.config else default_config
    config = load_config(config_path)

    run_cfg = config.get("run", {})
    scenario = config.get("scenario", {})
    env_cfg = scenario.get("env", {})
    rounds = int(run_cfg.get("rounds", 20))
    seed = int(run_cfg.get("seed", 42))
    agent_configs = parse_agent_configs(config)
    agent_ids = [c["id"] for c in agent_configs]

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_ids = {}

    for topo_key, topology_mode, visibility in TOPOLOGIES:
        print(f"\n=== Topology: {topo_key} ===")
        env = make_env(
            create_gridworld_env,
            width=int(env_cfg.get("width", 6)),
            height=int(env_cfg.get("height", 6)),
            agent_ids=agent_ids,
            landmarks=int(env_cfg.get("landmarks", 2)),
            observation_radius=int(env_cfg.get("observation_radius", 1)),
            max_cycles=int(env_cfg.get("max_cycles", 25)),
            seed=seed,
            render_mode=None,
        )
        session = Session.from_config({
            "shared_data": {"type": "file"},
            "scenario_name": f"gridworld_{topo_key}",
            "output_base": str(output_dir),
            "run_config": {"logging_level": 2},
            "topology": {"mode": topology_mode, **({"visibility": visibility} if visibility else {})},
            "policies": GRIDWORLD_POLICIES,
            "hub_id": "hub",
        })
        run_with_session(
            session,
            env,
            agent_configs,
            rounds,
            seed,
            energy_model=False,
            landmarks_total=env_cfg.get("landmarks"),
            render=False,
            print_every=0,
        )
        if session.run_id:
            run_ids[topo_key] = session.run_id
            run_path = Path(session.run_path)
            try:
                G = traceability.build_trace_graph(session.run_id, output_base=str(output_dir))
                traceability.render_trace_graph(G, str(run_path / f"trace_graph_{topo_key}.png"))
                attr = accountability.causal_attribution(session.run_id, output_base=str(output_dir))
                accountability.render_attribution_charts(attr, str(run_path / f"causal_attribution_{topo_key}.png"))
            except Exception as e:
                print(f"  Analysis: {e}")

    print(f"\nTopology comparison output: {output_dir}")
    for k, rid in run_ids.items():
        print(f"  {k}: run_id={rid}")


if __name__ == "__main__":
    main()
