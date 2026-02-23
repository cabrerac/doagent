"""Provenance chain walker — drill down into why a state was reached.

Given a record ID (or "last" for the final outcome), walk the provenance
chain backwards, showing the full attribution trail from outputs to inputs.

Usage:
    python provenance_walker.py <records_dir> [<record_id> | last] [--depth <n>]

Example:
    python provenance_walker.py output/gridworld_run_20260221_022506/records last
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


ACTION_NAMES = {0: "stay", 1: "left", 2: "right", 3: "up", 4: "down"}


def load_all_records(records_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load every JSONL file in the records directory, index by record ID."""
    index: Dict[str, Dict[str, Any]] = {}
    for jsonl_file in sorted(records_dir.glob("*.jsonl")):
        with jsonl_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    index[rec["id"]] = rec
    return index


def find_last_outcome(index: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """Find the outcome with the highest round number."""
    best_id, best_round = None, -1
    for rec in index.values():
        if rec["kind"] == "outcome":
            rnd = rec["payload"].get("round", 0)
            if rnd > best_round:
                best_round = rnd
                best_id = rec["id"]
    return best_id


def find_traces_to(target_id: str, index: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find all trace records whose to_id points to the given record."""
    return [
        rec for rec in index.values()
        if rec["kind"] == "trace" and rec["payload"].get("to_id") == target_id
    ]


def format_outcome_summary(rec: Dict[str, Any]) -> str:
    payload = rec["payload"]
    rnd = payload.get("round", "?")
    rewards = payload.get("rewards", {})
    actions = payload.get("actions", {})
    action_strs = [
        f"{agent}={ACTION_NAMES.get(a, str(a))}"
        for agent, a in sorted(actions.items())
    ]
    reward_strs = [f"{agent}={r}" for agent, r in sorted(rewards.items())]
    return (
        f"outcome round={rnd}  "
        f"actions=[{', '.join(action_strs)}]  "
        f"rewards=[{', '.join(reward_strs)}]"
    )


def format_agent_update_summary(rec: Dict[str, Any]) -> str:
    actor = rec.get("actor", "?")
    decision = rec["payload"].get("decision", {})
    response = decision.get("response", {}).get("decision", {})
    action = response.get("action")
    action_name = ACTION_NAMES.get(action, str(action)) if action is not None else "?"
    goal = decision.get("request", {}).get("goal", "?")
    return f"agent_update by {actor}  action={action_name}  goal={goal}"


def format_trace_summary(rec: Dict[str, Any]) -> str:
    payload = rec["payload"]
    actor = rec.get("actor", "?")
    rnd = payload.get("round", "?")
    relation = payload.get("relation", "?")
    notes = payload.get("notes", "")
    return f"trace round={rnd} by {actor}  relation={relation}  \"{notes}\""


def walk_provenance(
    record_id: str,
    index: Dict[str, Dict[str, Any]],
    max_depth: int = 4,
    *,
    _depth: int = 0,
    _visited: Optional[Set[str]] = None,
) -> List[str]:
    """Recursively walk the provenance chain, returning formatted lines."""
    if _visited is None:
        _visited = set()

    if record_id in _visited or _depth > max_depth:
        return [f"{'  ' * _depth}... (already visited or max depth)"]
    _visited.add(record_id)

    indent = "  " * _depth
    connector = "<- " if _depth > 0 else ""
    lines: List[str] = []

    if record_id == "initial_state":
        lines.append(f"{indent}{connector}[initial_state]")
        return lines

    rec = index.get(record_id)
    if rec is None:
        lines.append(f"{indent}{connector}[unknown record {record_id[:12]}...]")
        return lines

    kind = rec["kind"]

    if kind == "outcome":
        lines.append(f"{indent}{connector}{format_outcome_summary(rec)}")
        lines.append(f"{indent}  id: {rec['id'][:16]}...")

        provenance = rec.get("provenance", {})
        created_by = provenance.get("created_by", "?")
        lines.append(f"{indent}  created_by: {created_by}")

        derived_from = provenance.get("derived_from", [])
        if derived_from:
            lines.append(f"{indent}  derived_from ({len(derived_from)} agent updates):")
            for df_id in derived_from:
                lines.extend(walk_provenance(df_id, index, max_depth, _depth=_depth + 2, _visited=_visited))

        traces_in = find_traces_to(record_id, index)
        if traces_in:
            lines.append(f"{indent}  incoming traces ({len(traces_in)}):")
            for t in sorted(traces_in, key=lambda r: r.get("actor", "")):
                lines.extend(walk_provenance(t["id"], index, max_depth, _depth=_depth + 2, _visited=_visited))

    elif kind == "agent_update":
        lines.append(f"{indent}{connector}{format_agent_update_summary(rec)}")
        lines.append(f"{indent}  id: {rec['id'][:16]}...")
        provenance = rec.get("provenance", {})
        created_by = provenance.get("created_by", "?")
        lines.append(f"{indent}  provenance.created_by: {created_by}")

    elif kind == "trace":
        lines.append(f"{indent}{connector}{format_trace_summary(rec)}")
        from_id = rec["payload"].get("from_id", "?")
        enabled_by = rec["payload"].get("enabled_by_id", "?")
        lines.append(f"{indent}  enabled_by:")
        lines.extend(walk_provenance(enabled_by, index, max_depth, _depth=_depth + 2, _visited=_visited))
        lines.append(f"{indent}  from_state:")
        lines.extend(walk_provenance(from_id, index, max_depth, _depth=_depth + 2, _visited=_visited))

    else:
        lines.append(f"{indent}{connector}[{kind}] {rec['id'][:16]}...")

    return lines


def render_tree(
    record_id: str,
    index: Dict[str, Dict[str, Any]],
    output_dir: Path,
    max_depth: int = 3,
) -> None:
    """Render a simple tree diagram of the provenance chain using matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    nodes: List[Tuple[str, str, int]] = []  # (id, label, depth)
    edges: List[Tuple[str, str, str]] = []  # (child_id, parent_id, relation)
    visited: Set[str] = set()

    def _collect(rid: str, depth: int) -> None:
        if rid in visited or depth > max_depth:
            return
        visited.add(rid)

        if rid == "initial_state":
            nodes.append((rid, "initial_state", depth))
            return

        rec = index.get(rid)
        if rec is None:
            nodes.append((rid, f"?{rid[:8]}", depth))
            return

        kind = rec["kind"]
        if kind == "outcome":
            rnd = rec["payload"].get("round", "?")
            label = f"outcome\nround={rnd}"
            nodes.append((rid, label, depth))
            for df_id in rec.get("provenance", {}).get("derived_from", []):
                edges.append((df_id, rid, "derived_from"))
                _collect(df_id, depth + 1)
            for t in find_traces_to(rid, index):
                edges.append((t["id"], rid, "trace_to"))
                _collect(t["id"], depth + 1)
        elif kind == "agent_update":
            actor = rec.get("actor", "?")
            decision = rec["payload"].get("decision", {})
            action = decision.get("response", {}).get("decision", {}).get("action")
            action_name = ACTION_NAMES.get(action, str(action)) if action is not None else "?"
            label = f"{actor}\naction={action_name}"
            nodes.append((rid, label, depth))
        elif kind == "trace":
            actor = rec.get("actor", "?")
            rnd = rec["payload"].get("round", "?")
            label = f"trace\n{actor} r{rnd}"
            nodes.append((rid, label, depth))
            from_id = rec["payload"].get("from_id")
            enabled_by = rec["payload"].get("enabled_by_id")
            if enabled_by:
                edges.append((enabled_by, rid, "enabled_by"))
                _collect(enabled_by, depth + 1)
            if from_id:
                edges.append((from_id, rid, "from"))
                _collect(from_id, depth + 1)

    _collect(record_id, 0)

    if not nodes:
        return

    depth_groups: Dict[int, List[int]] = defaultdict(list)
    for i, (_, _, d) in enumerate(nodes):
        depth_groups[d].append(i)

    node_id_to_idx = {nid: i for i, (nid, _, _) in enumerate(nodes)}
    pos: Dict[int, Tuple[float, float]] = {}
    max_d = max(d for _, _, d in nodes) if nodes else 0
    for d, idxs in depth_groups.items():
        x = -d
        for j, idx in enumerate(idxs):
            spread = len(idxs)
            y = (j - (spread - 1) / 2) * 1.8
            pos[idx] = (x, y)

    fig, ax = plt.subplots(figsize=(max(8, (max_d + 1) * 3.5), max(5, len(nodes) * 0.7)))

    kind_colors = {"outcome": "#87ceeb", "agent_update": "#90EE90", "trace": "#FFD700", "initial_state": "#333333"}

    for i, (nid, label, depth) in enumerate(nodes):
        x, y = pos[i]
        rec = index.get(nid)
        kind = rec["kind"] if rec else "initial_state"
        if nid == "initial_state":
            kind = "initial_state"
        color = kind_colors.get(kind, "#DDDDDD")
        bbox = dict(boxstyle="round,pad=0.4", facecolor=color, edgecolor="#444", alpha=0.9)
        fontsize = 7 if len(nodes) > 20 else 8
        ax.text(x, y, label, ha="center", va="center", fontsize=fontsize, bbox=bbox, zorder=5)

    relation_colors = {"derived_from": "#1f77b4", "trace_to": "#d62728", "enabled_by": "#2ca02c", "from": "#ff7f0e"}

    for child_id, parent_id, relation in edges:
        ci = node_id_to_idx.get(child_id)
        pi = node_id_to_idx.get(parent_id)
        if ci is None or pi is None:
            continue
        cx, cy = pos[ci]
        px, py = pos[pi]
        color = relation_colors.get(relation, "#999999")
        ax.annotate(
            "", xy=(px, py), xytext=(cx, cy),
            arrowprops=dict(arrowstyle="->", color=color, lw=1.2, alpha=0.7),
            zorder=1,
        )

    import matplotlib.patches as mpatches
    legend_patches = [
        mpatches.Patch(color=c, label=k) for k, c in kind_colors.items()
    ] + [
        mpatches.Patch(color=c, label=f"edge: {k}") for k, c in relation_colors.items()
    ]
    ax.legend(handles=legend_patches, loc="upper left", fontsize=6, framealpha=0.8)

    ax.set_title("Provenance Chain — Why Did This State Happen?", fontsize=11, fontweight="bold")
    ax.axis("off")
    ax.set_xlim(ax.get_xlim()[0] - 1, ax.get_xlim()[1] + 1)
    fig.tight_layout()

    png_path = output_dir / "provenance_tree.png"
    pdf_path = output_dir / "provenance_tree.pdf"
    fig.savefig(png_path, dpi=200, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    print(f"\nProvenance tree saved to {png_path} and {pdf_path}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python provenance_walker.py <records_dir> [<record_id> | last] [--depth <n>]")
        sys.exit(1)

    records_dir = Path(sys.argv[1])
    output_dir = records_dir.parent

    max_depth = 4
    if "--depth" in sys.argv:
        idx = sys.argv.index("--depth")
        max_depth = int(sys.argv[idx + 1])

    if "--output-dir" in sys.argv:
        idx = sys.argv.index("--output-dir")
        output_dir = Path(sys.argv[idx + 1])

    index = load_all_records(records_dir)
    print(f"Loaded {len(index)} records from {records_dir}")

    record_id = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "last"
    if record_id == "last":
        record_id = find_last_outcome(index)
        if record_id is None:
            print("No outcome records found.")
            sys.exit(1)
        rnd = index[record_id]["payload"].get("round", "?")
        print(f"Starting from last outcome: round={rnd}, id={record_id[:16]}...")
    else:
        if record_id not in index:
            print(f"Record {record_id} not found in index.")
            sys.exit(1)

    print(f"\n{'='*70}")
    print(f"PROVENANCE CHAIN (max depth={max_depth})")
    print(f"{'='*70}")
    lines = walk_provenance(record_id, index, max_depth)
    for line in lines:
        print(line)
    print(f"{'='*70}")

    render_tree(record_id, index, output_dir, max_depth)


if __name__ == "__main__":
    main()
