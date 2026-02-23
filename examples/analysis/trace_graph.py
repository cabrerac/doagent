"""Trace graph visualization — build a directed state-transition graph from DOAgent records.

Nodes represent environment outcomes (states). Edges represent trace links,
colored by the agent whose decision enabled the transition. State deduplication
is visible as nodes with multiple incoming edges (convergence points).

Usage:
    python trace_graph.py <records_dir> [--output-dir <dir>]

Example:
    python trace_graph.py output/gridworld_run_20260221_022506/records
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def build_graph(
    traces: List[Dict[str, Any]],
    outcomes: List[Dict[str, Any]],
    agent_updates: List[Dict[str, Any]],
) -> Tuple[nx.MultiDiGraph, Dict[str, Dict[str, Any]]]:
    """Build a directed multigraph from trace records.

    Uses MultiDiGraph because multiple agents can create parallel edges
    between the same pair of states in a single round.

    Returns the graph and a metadata dict keyed by node id.
    """
    update_by_id = {r["id"]: r for r in agent_updates}

    G = nx.MultiDiGraph()

    node_meta: Dict[str, Dict[str, Any]] = {}

    for outcome in outcomes:
        oid = outcome["id"]
        rnd = outcome["payload"].get("round", "?")
        rewards = outcome["payload"].get("rewards", {})
        total_reward = sum(rewards.values())
        node_meta[oid] = {"round": rnd, "total_reward": total_reward, "type": "outcome"}
        G.add_node(oid, round=rnd, total_reward=total_reward)

    if any(t["payload"].get("from_id") == "initial_state" for t in traces):
        G.add_node("initial_state", round=0, total_reward=0)
        node_meta["initial_state"] = {"round": 0, "total_reward": 0, "type": "initial"}

    for trace in traces:
        payload = trace["payload"]
        from_id = payload["from_id"]
        to_id = payload["to_id"]
        enabled_by = payload.get("enabled_by_id", "")
        agent = trace.get("actor", "unknown")
        rnd = payload.get("round", 0)

        action = None
        if enabled_by in update_by_id:
            decision = update_by_id[enabled_by]["payload"].get("decision", {})
            response = decision.get("response", {}).get("decision", {})
            action = response.get("action")

        G.add_edge(
            from_id, to_id,
            agent=agent,
            round=rnd,
            action=action,
            enabled_by=enabled_by,
            trace_id=trace["id"],
        )

    return G, node_meta


ACTION_NAMES = {0: "stay", 1: "left", 2: "right", 3: "up", 4: "down"}

AGENT_COLORS = {
    "agent_0": "#1f77b4",
    "agent_1": "#ff7f0e",
    "agent_2": "#2ca02c",
    "agent_3": "#d62728",
}


def _compute_layout(
    G: nx.MultiDiGraph,
    node_meta: Dict[str, Dict[str, Any]],
    cols_per_row: int = 12,
) -> Tuple[Dict[str, Tuple[float, float]], int]:
    """Compute a wrapped grid layout that reads left-to-right, top-to-bottom.

    For chain-like graphs, this avoids the single squished horizontal line.
    For branching graphs, nodes at the same round share a column.
    """
    rounds = {n: node_meta.get(n, {}).get("round", 0) for n in G.nodes()}
    max_round = max(rounds.values()) if rounds else 0

    nodes_by_round: Dict[int, list] = defaultdict(list)
    for n in G.nodes():
        nodes_by_round[rounds[n]].append(n)

    is_chain = all(len(v) <= 1 for v in nodes_by_round.values())

    pos: Dict[str, Tuple[float, float]] = {}

    if is_chain and max_round > cols_per_row:
        seq = []
        for rnd in range(0, max_round + 1):
            for n in sorted(nodes_by_round.get(rnd, [])):
                seq.append(n)

        for idx, n in enumerate(seq):
            col = idx % cols_per_row
            row = idx // cols_per_row
            pos[n] = (col * 1.4, -row * 1.6)
    else:
        for rnd, nodes in sorted(nodes_by_round.items()):
            x = rnd * 1.4
            for i, n in enumerate(sorted(nodes)):
                spread = len(nodes)
                y = (i - (spread - 1) / 2) * 1.6
                pos[n] = (x, y)

    num_cols = min(max_round + 1, cols_per_row)
    return pos, num_cols


def render_graph(
    G: nx.MultiDiGraph,
    node_meta: Dict[str, Dict[str, Any]],
    output_dir: Path,
    *,
    max_label_nodes: int = 200,
    cols_per_row: int = 12,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyArrowPatch

    agents = sorted({d["agent"] for _, _, _, d in G.edges(data=True, keys=True)})
    color_map = {a: AGENT_COLORS.get(a, "#999999") for a in agents}

    in_degrees = dict(G.in_degree())

    node_colors = []
    for n in G.nodes():
        meta = node_meta.get(n, {})
        if meta.get("type") == "initial":
            node_colors.append("#333333")
        elif in_degrees.get(n, 0) > len(agents):
            node_colors.append("#ffd700")
        else:
            node_colors.append("#87ceeb")

    pos, num_cols = _compute_layout(G, node_meta, cols_per_row)

    rounds = {n: node_meta.get(n, {}).get("round", 0) for n in G.nodes()}
    max_round = max(rounds.values()) if rounds else 0
    num_rows = max(1, (max_round + cols_per_row) // cols_per_row) if max_round > cols_per_row else 1
    nodes_in_max_col = max(
        (sum(1 for n in G.nodes() if rounds[n] == r) for r in range(max_round + 1)),
        default=1,
    )

    fig_width = max(10, min(num_cols * 1.6, 22))
    fig_height = max(4, num_rows * 2.2 + nodes_in_max_col * 0.6)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    node_size = 350 if len(G.nodes()) <= 30 else (200 if len(G.nodes()) <= 60 else 120)
    node_sizes = [
        max(node_size, node_size + (in_degrees.get(n, 0) - len(agents)) * 60)
        for n in G.nodes()
    ]

    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_size=node_sizes,
        node_color=node_colors,
        edgecolors="#444444",
        linewidths=1.0,
        alpha=0.95,
    )

    edge_groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for u, v, _, d in G.edges(data=True, keys=True):
        edge_groups[(u, v)].append(d)

    n_agents = len(agents)
    agent_idx = {a: i for i, a in enumerate(agents)}

    for (u, v), edge_data_list in edge_groups.items():
        n_edges = len(edge_data_list)
        for j, d in enumerate(edge_data_list):
            agent = d.get("agent", "unknown")
            color = color_map.get(agent, "#999999")
            if n_edges == 1:
                rad = 0.0
            else:
                spread = 0.15 * min(n_edges, 6)
                rad = -spread / 2 + spread * j / max(n_edges - 1, 1)

            nx.draw_networkx_edges(
                G, pos, ax=ax,
                edgelist=[(u, v)],
                edge_color=[color],
                arrows=True,
                arrowsize=10,
                alpha=0.75,
                width=2.0,
                connectionstyle=f"arc3,rad={rad}",
                min_source_margin=8,
                min_target_margin=8,
            )

    if len(G.nodes()) <= max_label_nodes:
        labels = {}
        for n in G.nodes():
            meta = node_meta.get(n, {})
            if meta.get("type") == "initial":
                labels[n] = "S0"
            else:
                labels[n] = f"r{meta.get('round', '?')}"
        font_size = 8 if len(G.nodes()) <= 30 else (6.5 if len(G.nodes()) <= 60 else 5)
        nx.draw_networkx_labels(G, pos, labels, font_size=font_size, font_weight="bold", ax=ax)

    legend_patches = [
        mpatches.Patch(color=color_map[a], label=a) for a in agents
    ]
    legend_patches.append(mpatches.Patch(color="#ffd700", label="dedup convergence"))
    legend_patches.append(mpatches.Patch(color="#333333", label="initial state"))
    ax.legend(handles=legend_patches, loc="upper left", fontsize=8, framealpha=0.9)

    ax.set_title("DOAgent Trace Graph -- State Transitions by Agent", fontsize=13, fontweight="bold")
    ax.axis("off")
    fig.tight_layout()

    png_path = output_dir / "trace_graph.png"
    pdf_path = output_dir / "trace_graph.pdf"
    fig.savefig(png_path, dpi=200, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Trace graph saved to {png_path} and {pdf_path}")


def print_graph_stats(G: nx.MultiDiGraph, node_meta: Dict[str, Dict[str, Any]]) -> None:
    agents = sorted({d["agent"] for _, _, _, d in G.edges(data=True, keys=True)})
    unique_outcomes = sum(1 for n in G.nodes() if node_meta.get(n, {}).get("type") != "initial")

    in_degrees = dict(G.in_degree())
    dedup_nodes = [n for n, deg in in_degrees.items() if deg > len(agents)]

    edges_per_agent = defaultdict(int)
    for _, _, _, d in G.edges(data=True, keys=True):
        edges_per_agent[d["agent"]] += 1

    print(f"\n{'='*60}")
    print("TRACE GRAPH STATISTICS")
    print(f"{'='*60}")
    print(f"  Nodes (states):       {G.number_of_nodes()}")
    print(f"  Edges (transitions):  {G.number_of_edges()}")
    print(f"  Unique outcomes:      {unique_outcomes}")
    print(f"  Agents:               {', '.join(agents)}")
    print(f"  Dedup convergence:    {len(dedup_nodes)} nodes with >{len(agents)} incoming edges")
    print(f"\n  Transitions per agent:")
    for agent in agents:
        print(f"    {agent}: {edges_per_agent[agent]}")
    print(f"{'='*60}\n")


def export_dot(G: nx.MultiDiGraph, node_meta: Dict[str, Dict[str, Any]], output_dir: Path) -> None:
    dot_path = output_dir / "trace_graph.dot"
    with dot_path.open("w", encoding="utf-8") as f:
        f.write("digraph TraceGraph {\n")
        f.write('  rankdir=LR;\n')
        f.write('  node [shape=circle, style=filled, fontsize=8];\n')
        for n in G.nodes():
            meta = node_meta.get(n, {})
            short_id = n[:8] if n != "initial_state" else "S0"
            label = f"S₀" if meta.get("type") == "initial" else f"r{meta.get('round', '?')}"
            color = "#333333" if meta.get("type") == "initial" else "#87ceeb"
            f.write(f'  "{short_id}" [label="{label}", fillcolor="{color}"];\n')
        for u, v, _, d in G.edges(data=True, keys=True):
            u_short = u[:8] if u != "initial_state" else "S0"
            v_short = v[:8] if v != "initial_state" else "S0"
            agent = d.get("agent", "?")
            action = ACTION_NAMES.get(d.get("action"), str(d.get("action", "?")))
            color = AGENT_COLORS.get(agent, "#999999")
            f.write(f'  "{u_short}" -> "{v_short}" [label="{agent}:{action}", color="{color}", fontsize=7];\n')
        f.write("}\n")
    print(f"DOT file saved to {dot_path}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python trace_graph.py <records_dir> [--output-dir <dir>]")
        sys.exit(1)

    records_dir = Path(sys.argv[1])
    output_dir = records_dir.parent
    if "--output-dir" in sys.argv:
        idx = sys.argv.index("--output-dir")
        output_dir = Path(sys.argv[idx + 1])

    traces = load_jsonl(records_dir / "trace.jsonl")
    outcomes = load_jsonl(records_dir / "outcome.jsonl")
    agent_updates = load_jsonl(records_dir / "agent_update.jsonl")

    print(f"Loaded {len(traces)} traces, {len(outcomes)} outcomes, {len(agent_updates)} agent_updates")

    G, node_meta = build_graph(traces, outcomes, agent_updates)
    print_graph_stats(G, node_meta)
    render_graph(G, node_meta, output_dir)
    export_dot(G, node_meta, output_dir)


if __name__ == "__main__":
    main()
