"""Traceability analysis: trace graph, graph traversal, which actions influenced outcomes."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ._resolve import resolve_run


def _record_to_dict(record: Any) -> Dict[str, Any]:
    """Convert a SimpleRecord to a dict for JSON-friendly return values."""
    return {
        "id": record.id,
        "kind": record.kind,
        "actor": getattr(record, "actor", "?"),
        "timestamp": getattr(record, "timestamp", ""),
        "payload": record.payload,
        "provenance": getattr(record, "provenance", None) or {},
        "accountability": getattr(record, "accountability", None) or {},
    }


def build_trace_graph(
    run_id: str,
    *,
    output_base: str = "./output",
) -> Any:
    """Build a directed graph of how the run evolved: states and who moved between them.

    **What it means:** The trace graph is a directed graph of the run's execution.
    Nodes are outcomes (environment states at a given step). Edges are transitions
    between states, each tagged with the agent whose decision enabled that
    transition. Multiple agents can produce parallel edges between the same
    pair of states in a single round (e.g. multi-agent step), so the graph is
    a multigraph.

    **How it works:** The method loads outcome, trace, and agent_update records
    for the run. It creates one node per outcome (and optionally an initial_state
    node), and one edge per trace record from from_id to to_id, annotated with
    the acting agent and round. The result is a networkx MultiDiGraph (or
    equivalent) that can be passed to render_trace_graph or traversed for
    get_traces_to / get_traces_from.

    Args:
        run_id: Run identifier (same as the run's output folder name).
        output_base: Base directory for run folders; default "./output".

    Returns:
        A networkx MultiDiGraph with nodes for outcomes and edges for trace
        links. Node attributes: round, total_reward. Edge attributes: agent,
        round, action, enabled_by, trace_id. Graph attribute node_meta (dict
        keyed by node id) holds type (outcome/initial), round, total_reward.

    Raises:
        FileNotFoundError: If run metadata or records are not found.
        ImportError: If networkx is not installed.
    """
    try:
        import networkx as nx
    except ImportError as e:
        raise ImportError("build_trace_graph requires networkx") from e

    resolved = resolve_run(run_id, output_base=output_base)
    outcomes = list(resolved.inspect("outcome"))
    traces = list(resolved.inspect("trace"))
    agent_updates = list(resolved.inspect("agent_update"))

    update_by_id = {r.id: r for r in agent_updates}
    G = nx.MultiDiGraph()
    node_meta: Dict[str, Dict[str, Any]] = {}

    for outcome in outcomes:
        oid = outcome.id
        rnd = outcome.payload.get("round", "?")
        rewards = outcome.payload.get("rewards", {})
        total_reward = sum(rewards.values()) if isinstance(rewards, dict) else 0
        node_meta[oid] = {"round": rnd, "total_reward": total_reward, "type": "outcome"}
        G.add_node(oid, round=rnd, total_reward=total_reward)

    if any(t.payload.get("from_id") == "initial_state" for t in traces):
        G.add_node("initial_state", round=0, total_reward=0)
        node_meta["initial_state"] = {"round": 0, "total_reward": 0, "type": "initial"}

    for trace in traces:
        payload = trace.payload
        from_id = payload.get("from_id")
        to_id = payload.get("to_id")
        if from_id is None or to_id is None:
            continue
        enabled_by = payload.get("enabled_by_id", "")
        agent = getattr(trace, "actor", "unknown")
        rnd = payload.get("round", 0)
        action = None
        if enabled_by and update_by_id.get(enabled_by):
            dec = update_by_id[enabled_by].payload.get("decision", {})
            action = dec.get("response", {}).get("decision", {}).get("action")
        G.add_edge(
            from_id, to_id,
            agent=agent,
            round=rnd,
            action=action,
            enabled_by=enabled_by,
            trace_id=trace.id,
        )

    G.graph["node_meta"] = node_meta
    return G


def get_traces_to(
    record_id: str,
    run_id: str,
    *,
    output_base: str = "./output",
) -> List[Dict[str, Any]]:
    """Return the trace records that lead into the given record (incoming transitions).

    **What it means:** "Traces to" a record are the transitions that ended at
    this state — i.e. trace records whose to_id equals the given record_id.
    They answer "which actions (and which agents) led to this outcome?"

    **How it works:** The method loads trace records for the run and filters
    those whose payload to_id matches record_id. The result is a list of
    trace records (as dicts), sorted by round then actor.

    Args:
        record_id: The outcome or record id to query (destination of traces).
        run_id: Run identifier (same as the run's output folder name).
        output_base: Base directory for run folders; default "./output".

    Returns:
        List of trace records as dicts (id, kind, actor, timestamp, payload, ...)
        that point to record_id.

    Raises:
        FileNotFoundError: If run metadata or records are not found.
    """
    resolved = resolve_run(run_id, output_base=output_base)
    traces = [
        r for r in resolved.inspect("trace")
        if r.payload.get("to_id") == record_id
    ]
    out = [_record_to_dict(r) for r in traces]
    out.sort(key=lambda d: (d.get("payload", {}).get("round", 0), d.get("actor", "")))
    return out


def get_traces_from(
    record_id: str,
    run_id: str,
    *,
    output_base: str = "./output",
) -> List[Dict[str, Any]]:
    """Return the trace records that leave from the given record (outgoing transitions).

    **What it means:** "Traces from" a record are the transitions that started
    from this state — i.e. trace records whose from_id equals the given
    record_id. They answer "what transitions did this state lead to, and
    which agents enabled them?"

    **How it works:** The method loads trace records for the run and filters
    those whose payload from_id matches record_id. The result is a list of
    trace records (as dicts), sorted by round then actor.

    Args:
        record_id: The outcome or record id to query (source of traces).
        run_id: Run identifier (same as the run's output folder name).
        output_base: Base directory for run folders; default "./output".

    Returns:
        List of trace records as dicts that start from record_id.

    Raises:
        FileNotFoundError: If run metadata or records are not found.
    """
    resolved = resolve_run(run_id, output_base=output_base)
    traces = [
        r for r in resolved.inspect("trace")
        if r.payload.get("from_id") == record_id
    ]
    out = [_record_to_dict(r) for r in traces]
    out.sort(key=lambda d: (d.get("payload", {}).get("round", 0), d.get("actor", "")))
    return out


def _compute_layout(
    G: Any,
    node_meta: Dict[str, Dict[str, Any]],
    cols_per_row: int = 12,
) -> Tuple[Dict[str, Tuple[float, float]], int]:
    """Compute a wrapped grid layout (left-to-right, top-to-bottom)."""
    rounds = {n: node_meta.get(n, {}).get("round", 0) for n in G.nodes()}
    max_round = max((r for r in rounds.values() if isinstance(r, (int, float))), default=0)
    if not isinstance(max_round, (int, float)):
        max_round = 0
    nodes_by_round: Dict[int, list] = defaultdict(list)
    for n in G.nodes():
        r = rounds.get(n, 0)
        if isinstance(r, (int, float)):
            nodes_by_round[int(r)].append(n)
        else:
            nodes_by_round[0].append(n)
    is_chain = all(len(v) <= 1 for v in nodes_by_round.values())
    pos: Dict[str, Tuple[float, float]] = {}
    if is_chain and max_round > cols_per_row:
        seq = []
        for rnd in range(0, int(max_round) + 1):
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
    num_cols = min(int(max_round) + 1, cols_per_row)
    return pos, num_cols


def render_trace_graph(graph: Any, output_path: str) -> None:
    """Draw the trace graph to a file (PNG, PDF, or DOT).

    **What it means:** A visualisation of the trace graph — nodes as states,
    edges as transitions, with layout and optional coloring by agent or round.
    Useful for inspecting run structure, convergence points, and agent roles.

    **How it works:** The method takes an already-built graph (e.g. from
    build_trace_graph), computes a layout, and writes the figure to
    output_path. The output format is inferred from the path extension
    (e.g. .png, .pdf, .dot).

    Args:
        graph: A trace graph produced by build_trace_graph (networkx
            MultiDiGraph with graph.node_meta and edge attributes).
        output_path: Path for the output file (e.g. graph.png, graph.pdf, graph.dot).

    Raises:
        ImportError: If networkx (for .dot) or matplotlib (for .png/.pdf) is not installed.
    """
    try:
        import networkx as nx
    except ImportError as e:
        raise ImportError("render_trace_graph requires networkx") from e

    node_meta = getattr(graph, "graph", {}).get("node_meta", {})
    if not node_meta and hasattr(graph, "graph"):
        node_meta = graph.graph.get("node_meta", {})

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ext = path.suffix.lower()

    if ext == ".dot":
        _render_dot(graph, node_meta, path)
        return

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError as e:
        raise ImportError("render_trace_graph for PNG/PDF requires matplotlib") from e

    agents = sorted({d.get("agent", "unknown") for _, _, d in graph.edges(data=True)})
    agent_colors = {"agent_0": "#1f77b4", "agent_1": "#ff7f0e", "agent_2": "#2ca02c", "agent_3": "#d62728"}
    color_map = {a: agent_colors.get(a, "#999999") for a in agents}
    in_degrees = dict(graph.in_degree())
    node_colors = []
    for n in graph.nodes():
        meta = node_meta.get(n, {})
        if meta.get("type") == "initial":
            node_colors.append("#333333")
        elif in_degrees.get(n, 0) > max(len(agents), 1):
            node_colors.append("#ffd700")
        else:
            node_colors.append("#87ceeb")

    pos, num_cols = _compute_layout(graph, node_meta, cols_per_row=12)
    rounds = {n: node_meta.get(n, {}).get("round", 0) for n in graph.nodes()}
    max_round = max((r for r in rounds.values() if isinstance(r, (int, float))), default=0)
    if not isinstance(max_round, (int, float)):
        max_round = 0
    num_rows = max(1, (int(max_round) + 12) // 12) if max_round > 12 else 1
    nodes_in_max_col = max(
        (sum(1 for n in graph.nodes() if rounds.get(n) == r) for r in range(int(max_round) + 1)),
        default=1,
    )
    fig_width = max(10, min(num_cols * 1.6, 22))
    fig_height = max(4, num_rows * 2.2 + nodes_in_max_col * 0.6)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    node_size = 350 if graph.number_of_nodes() <= 30 else (200 if graph.number_of_nodes() <= 60 else 120)
    node_sizes = [
        max(node_size, node_size + (in_degrees.get(n, 0) - max(len(agents), 1)) * 60)
        for n in graph.nodes()
    ]
    nx.draw_networkx_nodes(
        graph, pos, ax=ax,
        node_size=node_sizes,
        node_color=node_colors,
        edgecolors="#444444",
        linewidths=1.0,
        alpha=0.95,
    )
    edge_groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for u, v, d in graph.edges(data=True):
        edge_groups[(u, v)].append(d)
    for (u, v), edge_data_list in edge_groups.items():
        n_edges = len(edge_data_list)
        for j, d in enumerate(edge_data_list):
            agent = d.get("agent", "unknown")
            color = color_map.get(agent, "#999999")
            rad = 0.0 if n_edges == 1 else (-0.15 * min(n_edges, 6) / 2 + 0.15 * min(n_edges, 6) * j / max(n_edges - 1, 1))
            nx.draw_networkx_edges(
                graph, pos, ax=ax,
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
    max_label_nodes = 200
    if graph.number_of_nodes() <= max_label_nodes:
        labels = {}
        for n in graph.nodes():
            meta = node_meta.get(n, {})
            labels[n] = "S0" if meta.get("type") == "initial" else f"r{meta.get('round', '?')}"
        font_size = 8 if graph.number_of_nodes() <= 30 else (6.5 if graph.number_of_nodes() <= 60 else 5)
        nx.draw_networkx_labels(graph, pos, labels, font_size=font_size, font_weight="bold", ax=ax)
    legend_patches = [mpatches.Patch(color=color_map[a], label=a) for a in agents]
    legend_patches.append(mpatches.Patch(color="#ffd700", label="dedup convergence"))
    legend_patches.append(mpatches.Patch(color="#333333", label="initial state"))
    ax.legend(handles=legend_patches, loc="upper left", fontsize=8, framealpha=0.9)
    ax.set_title("DOAgent Trace Graph — State Transitions by Agent", fontsize=13, fontweight="bold")
    ax.axis("off")
    fig.tight_layout()
    if ext == ".png":
        fig.savefig(path, dpi=200, bbox_inches="tight")
    else:
        fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _render_dot(graph: Any, node_meta: Dict[str, Dict[str, Any]], path: Path) -> None:
    """Write the trace graph in DOT format."""
    import networkx as nx
    lines = ["digraph TraceGraph {", "  rankdir=LR;", "  node [shape=circle, style=filled, fontsize=8];"]
    for n in graph.nodes():
        meta = node_meta.get(n, {})
        short_id = n[:8] if n != "initial_state" else "S0"
        label = "S0" if meta.get("type") == "initial" else f"r{meta.get('round', '?')}"
        color = "#333333" if meta.get("type") == "initial" else "#87ceeb"
        lines.append(f'  "{short_id}" [label="{label}", fillcolor="{color}"];')
    for u, v, d in graph.edges(data=True):
        u_short = u[:8] if u != "initial_state" else "S0"
        v_short = v[:8] if v != "initial_state" else "S0"
        agent = d.get("agent", "?")
        action = d.get("action", "?")
        lines.append(f'  "{u_short}" -> "{v_short}" [label="{agent}:{action}", fontsize=7];')
    lines.append("}")
    path.write_text("\n".join(lines), encoding="utf-8")
