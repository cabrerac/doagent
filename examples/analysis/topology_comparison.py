"""Topology comparison — run gridworld with 3 topologies and compare trace graphs + attribution.

Runs the gridworld simulation under centralised, peer-to-peer, and federated
topologies using the same seed, then produces a side-by-side comparison of
trace graph statistics and causal attribution.

Usage:
    python topology_comparison.py [--run] [--output-dir <dir>]
    python topology_comparison.py --dirs <cent_records> <p2p_records> <fed_records>

Modes:
    --run    Run all three topologies (requires gridworld dependencies)
    --dirs   Analyze pre-existing output directories (3 records dirs)

Example:
    python topology_comparison.py --run --output-dir output/topo_comparison
    python topology_comparison.py --dirs output/cent/records output/p2p/records output/fed/records
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from trace_graph import build_graph, load_jsonl
from causal_attribution import compute_attribution


TOPOLOGIES = ["centralised", "peer_to_peer", "federated"]
TOPO_LABELS = {"centralised": "Centralised", "peer_to_peer": "Peer-to-Peer", "federated": "Federated"}
TOPO_COLORS = {"centralised": "#1f77b4", "peer_to_peer": "#ff7f0e", "federated": "#2ca02c"}


def run_topologies(output_dir: Path) -> Dict[str, Path]:
    """Run gridworld under each topology and return records directory paths."""
    from examples.validation.gridworld.gridworld_validation import (
        load_config,
        parse_topology,
        parse_agent_configs,
        run_with_session,
    )
    from doagent.core import FileSharedData, TopologyConfig, Topology
    from doagent.validation import PolicyRegistry
    from doagent.validation.gridworld import make_grid_env, register_gridworld_policies

    configs_dir = Path(__file__).resolve().parent / "configs"
    records_dirs: Dict[str, Path] = {}

    for topo_name in TOPOLOGIES:
        config_path = configs_dir / f"{topo_name}.yaml"
        config = load_config(config_path)

        run_cfg = config.get("run", {})
        scenario = config.get("scenario", {})
        env_cfg = scenario.get("env", {})
        rounds = int(run_cfg.get("rounds", 50))
        seed = int(run_cfg.get("seed", 42))

        agent_configs = parse_agent_configs(config)
        agent_ids = [c["id"] for c in agent_configs]
        topology_cfg, visibility = parse_topology(config)

        env = make_grid_env(
            width=int(env_cfg.get("width", 15)),
            height=int(env_cfg.get("height", 15)),
            agent_ids=agent_ids,
            landmarks=int(env_cfg.get("landmarks", 0)),
            observation_radius=int(env_cfg.get("observation_radius", 1)),
            max_cycles=int(env_cfg.get("max_cycles", 100)),
            seed=seed,
            render_mode=None,
        )

        registry = PolicyRegistry()
        register_gridworld_policies(registry)

        topo_dir = output_dir / topo_name
        records_dir = topo_dir / "records"
        file_shared = FileSharedData(records_dir)

        print(f"\n--- Running {TOPO_LABELS[topo_name]} topology ---")
        summary = run_with_session(
            file_shared,
            env=env,
            registry=registry,
            configs=agent_configs,
            rounds=rounds,
            seed=seed,
            topology_cfg=topology_cfg,
            visibility=visibility,
        )
        records_dirs[topo_name] = records_dir
        agent_policies = {c["id"]: c["policy"].get("name", c["id"]) for c in agent_configs}
        (topo_dir / "agent_policies.json").write_text(json.dumps(agent_policies, indent=2), encoding="utf-8")
        print(f"  Coverage: {summary['coverage']*100:.1f}%, Rounds: {summary['outcomes']}")

    return records_dirs


def load_topology_data(records_dirs: Dict[str, Path]) -> Dict[str, Dict[str, Any]]:
    """Load and compute statistics for each topology."""
    data: Dict[str, Dict[str, Any]] = {}

    for topo_name, rdir in records_dirs.items():
        traces = load_jsonl(rdir / "trace.jsonl")
        outcomes = load_jsonl(rdir / "outcome.jsonl")
        agent_updates = load_jsonl(rdir / "agent_update.jsonl")

        G, node_meta = build_graph(traces, outcomes, agent_updates)
        attribution = compute_attribution(traces, outcomes, agent_updates)

        in_degrees = dict(G.in_degree())
        agents = sorted({d["agent"] for _, _, _, d in G.edges(data=True, keys=True)}) if G.edges() else []
        dedup_nodes = sum(1 for _, deg in in_degrees.items() if deg > len(agents))

        data[topo_name] = {
            "graph": G,
            "node_meta": node_meta,
            "attribution": attribution,
            "num_nodes": G.number_of_nodes(),
            "num_edges": G.number_of_edges(),
            "dedup_convergence": dedup_nodes,
            "agents": agents,
            "traces": len(traces),
            "outcomes": len(outcomes),
        }

    return data


def print_comparison(data: Dict[str, Dict[str, Any]]) -> None:
    print(f"\n{'='*80}")
    print("TOPOLOGY COMPARISON")
    print(f"{'='*80}\n")

    header = f"  {'Metric':<30}"
    for topo in TOPOLOGIES:
        if topo in data:
            header += f" {TOPO_LABELS[topo]:>16}"
    print(header)
    print(f"  {'-'*78}")

    metrics = [
        ("Outcomes", lambda d: str(d["outcomes"])),
        ("Trace edges", lambda d: str(d["num_edges"])),
        ("Graph nodes", lambda d: str(d["num_nodes"])),
        ("Dedup convergence nodes", lambda d: str(d["dedup_convergence"])),
        ("Total cells discovered", lambda d: str(len(d["attribution"]["global_known"]))),
    ]
    for label, fn in metrics:
        row = f"  {label:<30}"
        for topo in TOPOLOGIES:
            if topo in data:
                row += f" {fn(data[topo]):>16}"
        print(row)

    print()
    for topo in TOPOLOGIES:
        if topo not in data:
            continue
        attr = data[topo]["attribution"]
        print(f"  {TOPO_LABELS[topo]} agent discovery:")
        for agent in attr["agents"]:
            d = len(attr["agent_discovered"].get(agent, set()))
            p = attr["agent_productive"].get(agent, 0)
            r = attr["agent_redundant"].get(agent, 0)
            total = p + r
            eff = f"{p / total * 100:.0f}%" if total > 0 else "N/A"
            print(f"    {agent}: {d:>4} cells, {eff} effective ({p} productive / {r} redundant)")
        print()

    print(f"{'='*80}\n")


def render_comparison(
    data: Dict[str, Dict[str, Any]],
    output_dir: Path,
    agent_labels: Dict[str, str] | None = None,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    present = [t for t in TOPOLOGIES if t in data]
    n_topos = len(present)
    if n_topos == 0:
        return

    all_agents = sorted(set(
        a for t in present for a in data[t]["attribution"]["agents"]
    ))
    agent_labels = agent_labels or {}
    agent_display = [f"{a} ({agent_labels[a]})" if a in agent_labels else a for a in all_agents]

    FONT_TITLE = 15
    FONT_AXIS = 13
    FONT_TICK = 12
    FONT_LEGEND = 11
    FONT_SUPTITLE = 16

    fig, axes = plt.subplots(2, 2, figsize=(16, 11))

    AGENT_COLORS = {
        "agent_0": "#1f77b4", "agent_1": "#ff7f0e",
        "agent_2": "#2ca02c", "agent_3": "#d62728",
    }

    # --- Chart 1: Graph structure comparison (grouped bar) ---
    ax1 = axes[0][0]
    x = range(n_topos)
    labels = [TOPO_LABELS[t] for t in present]
    nodes = [data[t]["num_nodes"] for t in present]
    edges = [data[t]["num_edges"] for t in present]
    dedup = [data[t]["dedup_convergence"] for t in present]

    width = 0.25
    ax1.bar([i - width for i in x], nodes, width, label="Nodes", color="#87ceeb", edgecolor="#444")
    ax1.bar(list(x), edges, width, label="Edges", color="#FFD700", edgecolor="#444")
    ax1.bar([i + width for i in x], dedup, width, label="Dedup nodes", color="#FF6B6B", edgecolor="#444")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(labels, fontsize=FONT_TICK)
    ax1.set_ylabel("Count", fontsize=FONT_AXIS)
    ax1.set_title("Trace Graph Structure", fontsize=FONT_TITLE, fontweight="bold")
    ax1.legend(fontsize=FONT_LEGEND)
    ax1.tick_params(axis="y", labelsize=FONT_TICK)
    ax1.grid(True, alpha=0.3, axis="y")

    # --- Chart 2: Total discovery per topology (bar) ---
    ax2 = axes[0][1]
    totals = [len(data[t]["attribution"]["global_known"]) for t in present]
    colors = [TOPO_COLORS[t] for t in present]
    bars = ax2.bar(labels, totals, color=colors, edgecolor="#444")
    for bar, total in zip(bars, totals):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 str(total), ha="center", va="bottom", fontsize=FONT_TICK, fontweight="bold")
    ax2.set_ylabel("Cells discovered", fontsize=FONT_AXIS)
    ax2.set_title("Total Coverage by Topology", fontsize=FONT_TITLE, fontweight="bold")
    ax2.tick_params(axis="both", labelsize=FONT_TICK)
    ax2.grid(True, alpha=0.3, axis="y")

    # --- Chart 3: Per-agent discovery across topologies (grouped bar) ---
    ax3 = axes[1][0]
    n_agents = len(all_agents)
    bar_width = 0.8 / max(n_topos, 1)

    for i, topo in enumerate(present):
        attr = data[topo]["attribution"]
        vals = [len(attr["agent_discovered"].get(a, set())) for a in all_agents]
        positions = [j + i * bar_width for j in range(n_agents)]
        ax3.bar(positions, vals, bar_width, label=TOPO_LABELS[topo],
                color=TOPO_COLORS[topo], edgecolor="#444", alpha=0.85)

    ax3.set_xticks([j + bar_width * (n_topos - 1) / 2 for j in range(n_agents)])
    ax3.set_xticklabels(agent_display, fontsize=FONT_TICK, rotation=15, ha="right")
    ax3.set_ylabel("Cells discovered", fontsize=FONT_AXIS)
    ax3.set_title("Per-Agent Discovery by Topology", fontsize=FONT_TITLE, fontweight="bold")
    ax3.legend(fontsize=FONT_LEGEND)
    ax3.tick_params(axis="y", labelsize=FONT_TICK)
    ax3.grid(True, alpha=0.3, axis="y")

    # --- Chart 4: Effectiveness across topologies ---
    ax4 = axes[1][1]
    for i, topo in enumerate(present):
        attr = data[topo]["attribution"]
        effs = []
        for a in all_agents:
            p = attr["agent_productive"].get(a, 0)
            r = attr["agent_redundant"].get(a, 0)
            effs.append(p / (p + r) * 100 if (p + r) > 0 else 0)
        positions = [j + i * bar_width for j in range(n_agents)]
        ax4.bar(positions, effs, bar_width, label=TOPO_LABELS[topo],
                color=TOPO_COLORS[topo], edgecolor="#444", alpha=0.85)

    ax4.set_xticks([j + bar_width * (n_topos - 1) / 2 for j in range(n_agents)])
    ax4.set_xticklabels(agent_display, fontsize=FONT_TICK, rotation=15, ha="right")
    ax4.set_ylabel("Effectiveness (%)", fontsize=FONT_AXIS)
    ax4.set_title("Decision Effectiveness by Topology", fontsize=FONT_TITLE, fontweight="bold")
    ax4.legend(fontsize=FONT_LEGEND)
    ax4.tick_params(axis="y", labelsize=FONT_TICK)
    ax4.grid(True, alpha=0.3, axis="y")
    ax4.set_ylim(0, 110)

    fig.suptitle(
        "DOAgent Topology Comparison\n"
        "Same agents, same seed, different coordination -- all from trace data",
        fontsize=FONT_SUPTITLE, fontweight="bold", y=1.01,
    )
    fig.tight_layout()

    png_path = output_dir / "topology_comparison.png"
    pdf_path = output_dir / "topology_comparison.pdf"
    fig.savefig(png_path, dpi=200, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Comparison charts saved to {png_path} and {pdf_path}")


def main() -> None:
    output_dir = Path("output/topo_comparison")

    if "--output-dir" in sys.argv:
        idx = sys.argv.index("--output-dir")
        output_dir = Path(sys.argv[idx + 1])

    if "--dirs" in sys.argv:
        idx = sys.argv.index("--dirs")
        dirs = sys.argv[idx + 1: idx + 4]
        if len(dirs) < 3:
            print("Error: --dirs requires 3 record directories (centralised, p2p, federated)")
            sys.exit(1)
        records_dirs = dict(zip(TOPOLOGIES, [Path(d) for d in dirs]))
    elif "--run" in sys.argv:
        output_dir.mkdir(parents=True, exist_ok=True)
        records_dirs = run_topologies(output_dir)
    else:
        print("Usage:")
        print("  python topology_comparison.py --run [--output-dir <dir>]")
        print("  python topology_comparison.py --dirs <cent_recs> <p2p_recs> <fed_recs> [--output-dir <dir>]")
        sys.exit(1)

    data = load_topology_data(records_dirs)
    print_comparison(data)
    present = [t for t in TOPOLOGIES if t in data]
    agent_labels: Dict[str, str] = {}
    if present:
        first_records = records_dirs[present[0]]
        policies_path = first_records.parent / "agent_policies.json"
        if policies_path.exists():
            with open(policies_path, encoding="utf-8") as f:
                agent_labels = json.load(f)
    render_comparison(data, output_dir, agent_labels=agent_labels)


if __name__ == "__main__":
    main()
