"""Provenance analysis: chain walking, who created what from what."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ._resolve import resolve_run


def _record_to_dict(record: Any) -> Dict[str, Any]:
    """Turn a SimpleRecord into a dict for index lookups (id, kind, payload, provenance, actor)."""
    return {
        "id": record.id,
        "kind": record.kind,
        "payload": record.payload,
        "provenance": getattr(record, "provenance", None) or {},
        "actor": getattr(record, "actor", "?"),
    }


def _build_index(resolved: Any) -> Dict[str, Dict[str, Any]]:
    """Build id -> record dict from outcome, trace, and agent_update records."""
    index: Dict[str, Dict[str, Any]] = {}
    for kind in ("outcome", "trace", "agent_update"):
        for record in resolved.inspect(kind):
            d = _record_to_dict(record)
            index[d["id"]] = d
    return index


def _find_last_outcome(index: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """Return the outcome id with the highest round number, or None."""
    best_id: Optional[str] = None
    best_round = -1
    for rec in index.values():
        if rec.get("kind") == "outcome":
            rnd = rec.get("payload", {}).get("round", 0)
            if rnd > best_round:
                best_round = rnd
                best_id = rec["id"]
    return best_id


def _find_traces_to(target_id: str, index: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return trace records whose payload to_id equals target_id."""
    return [
        rec for rec in index.values()
        if rec.get("kind") == "trace" and rec.get("payload", {}).get("to_id") == target_id
    ]


def _summary_outcome(rec: Dict[str, Any]) -> str:
    """Short summary line for an outcome record."""
    payload = rec.get("payload", {})
    rnd = payload.get("round", "?")
    rewards = payload.get("rewards", {})
    actions = payload.get("actions", {})
    action_str = ", ".join(f"{a}={v}" for a, v in sorted(actions.items()))
    reward_str = ", ".join(f"{a}={v}" for a, v in sorted(rewards.items()))
    return f"outcome round={rnd}  actions=[{action_str}]  rewards=[{reward_str}]"


def _summary_agent_update(rec: Dict[str, Any]) -> str:
    """Short summary line for an agent_update record."""
    actor = rec.get("actor", "?")
    decision = rec.get("payload", {}).get("decision", {})
    response = decision.get("response", {}).get("decision", {})
    action = response.get("action", "?")
    goal = decision.get("request", {}).get("goal", "?")
    return f"agent_update by {actor}  action={action}  goal={goal}"


def _summary_trace(rec: Dict[str, Any]) -> str:
    """Short summary line for a trace record."""
    payload = rec.get("payload", {})
    actor = rec.get("actor", "?")
    rnd = payload.get("round", "?")
    relation = payload.get("relation", "?")
    notes = payload.get("notes", "")
    return f"trace round={rnd} by {actor}  relation={relation}  \"{notes}\""


def _walk_chain_rec(
    record_id: str,
    index: Dict[str, Dict[str, Any]],
    max_depth: int,
    depth: int,
    visited: Set[str],
) -> Dict[str, Any]:
    """Recursively build one node of the chain tree."""
    if record_id in visited or depth > max_depth:
        return {
            "record_id": record_id,
            "kind": "_pruned",
            "depth": depth,
            "summary": "... (already visited or max depth)",
            "children": [],
        }
    visited.add(record_id)

    if record_id == "initial_state":
        return {
            "record_id": record_id,
            "kind": "initial_state",
            "depth": depth,
            "summary": "[initial_state]",
            "children": [],
        }

    rec = index.get(record_id)
    if rec is None:
        return {
            "record_id": record_id,
            "kind": "unknown",
            "depth": depth,
            "summary": f"[unknown record {record_id[:12]}...]",
            "children": [],
        }

    kind = rec.get("kind", "?")
    if kind == "outcome":
        summary = _summary_outcome(rec)
        children: List[Dict[str, Any]] = []
        for df_id in rec.get("provenance", {}).get("derived_from", []):
            children.append(_walk_chain_rec(df_id, index, max_depth, depth + 1, visited))
        for t in _find_traces_to(record_id, index):
            children.append(_walk_chain_rec(t["id"], index, max_depth, depth + 1, visited))
        return {
            "record_id": record_id,
            "kind": kind,
            "depth": depth,
            "summary": summary,
            "children": children,
        }
    if kind == "agent_update":
        return {
            "record_id": record_id,
            "kind": kind,
            "depth": depth,
            "summary": _summary_agent_update(rec),
            "children": [],
        }
    if kind == "trace":
        from_id = rec.get("payload", {}).get("from_id")
        enabled_by = rec.get("payload", {}).get("enabled_by_id")
        children = []
        if enabled_by:
            children.append(_walk_chain_rec(enabled_by, index, max_depth, depth + 1, visited))
        if from_id:
            children.append(_walk_chain_rec(from_id, index, max_depth, depth + 1, visited))
        return {
            "record_id": record_id,
            "kind": kind,
            "depth": depth,
            "summary": _summary_trace(rec),
            "children": children,
        }

    return {
        "record_id": record_id,
        "kind": kind,
        "depth": depth,
        "summary": f"[{kind}] {record_id[:16]}...",
        "children": [],
    }


def walk_chain(
    record_id: str,
    run_id: str,
    *,
    max_depth: Optional[int] = None,
    output_base: str = "./output",
) -> Any:
    """Walk the provenance chain backwards from a record and return a structured chain.

    **What it means:** The provenance chain is the linkage from a record back to the
    records it was derived from. For example, an outcome points to the trace that
    produced it, and that trace points to the agent decision and the prior state.
    Walking the chain answers "why was this state or outcome reached?"

    **How it works:** Starting from the given record_id, the method follows
    derived_from / trace from_id–to_id links backwards through outcomes, traces,
    and agent_update records. The walk can be limited by max_depth. The result
    is a structured representation of the chain (e.g. nested dict or list of
    steps) suitable for inspection or passing to render_chain_tree.

    Args:
        record_id: The record to start from (e.g. an outcome id, or "last" for
            the final outcome of the run).
        run_id: Run identifier (same as the run's output folder name).
        max_depth: Optional maximum number of steps to walk backwards; None = no limit.
        output_base: Base directory for run folders; default "./output".

    Returns:
        A nested dict with keys record_id, kind, depth, summary, and children
        (list of same structure), representing the provenance chain tree.

    Raises:
        FileNotFoundError: If run metadata or records are not found.
        ValueError: If record_id is "last" but the run has no outcomes, or if
            record_id is not "last"/"initial_state" and the record is not in the run.
    """
    resolved = resolve_run(run_id, output_base=output_base)
    index = _build_index(resolved)
    effective_id = record_id
    if record_id == "last":
        effective_id = _find_last_outcome(index)
        if effective_id is None:
            raise ValueError("No outcome records found in run; cannot resolve 'last'")
    elif record_id != "initial_state" and effective_id not in index:
        raise ValueError(f"Record {record_id!r} not found in run")

    depth_limit = max_depth if max_depth is not None else 100
    return _walk_chain_rec(effective_id, index, depth_limit, 0, set())


def _collect_nodes_edges(
    record_id: str,
    index: Dict[str, Dict[str, Any]],
    max_depth: int,
    depth: int,
    visited: Set[str],
    nodes: List[tuple],
    edges: List[tuple],
) -> None:
    """Collect (id, label, depth) and (child_id, parent_id, relation) for rendering."""
    if record_id in visited or depth > max_depth:
        return
    visited.add(record_id)

    if record_id == "initial_state":
        nodes.append((record_id, "initial_state", depth))
        return

    rec = index.get(record_id)
    if rec is None:
        nodes.append((record_id, f"?{record_id[:8]}", depth))
        return

    kind = rec.get("kind", "?")
    if kind == "outcome":
        rnd = rec.get("payload", {}).get("round", "?")
        label = f"outcome\nround={rnd}"
        nodes.append((record_id, label, depth))
        for df_id in rec.get("provenance", {}).get("derived_from", []):
            edges.append((df_id, record_id, "derived_from"))
            _collect_nodes_edges(df_id, index, max_depth, depth + 1, visited, nodes, edges)
        for t in _find_traces_to(record_id, index):
            edges.append((t["id"], record_id, "trace_to"))
            _collect_nodes_edges(t["id"], index, max_depth, depth + 1, visited, nodes, edges)
    elif kind == "agent_update":
        actor = rec.get("actor", "?")
        action = rec.get("payload", {}).get("decision", {}).get("response", {}).get("decision", {}).get("action", "?")
        label = f"{actor}\naction={action}"
        nodes.append((record_id, label, depth))
    elif kind == "trace":
        actor = rec.get("actor", "?")
        rnd = rec.get("payload", {}).get("round", "?")
        label = f"trace\n{actor} r{rnd}"
        nodes.append((record_id, label, depth))
        enabled_by = rec.get("payload", {}).get("enabled_by_id")
        from_id = rec.get("payload", {}).get("from_id")
        if enabled_by:
            edges.append((enabled_by, record_id, "enabled_by"))
            _collect_nodes_edges(enabled_by, index, max_depth, depth + 1, visited, nodes, edges)
        if from_id:
            edges.append((from_id, record_id, "from"))
            _collect_nodes_edges(from_id, index, max_depth, depth + 1, visited, nodes, edges)
    else:
        nodes.append((record_id, f"{kind} {record_id[:8]}", depth))


def render_chain_tree(
    record_id: str,
    run_id: str,
    output_path: str,
    *,
    output_base: str = "./output",
) -> None:
    """Produce a tree diagram of the provenance chain and write it to a file.

    **What it means:** A chain tree is a visual representation of the same
    provenance chain that walk_chain returns: which records led to which,
    from a given record back to earlier states and decisions.

    **How it works:** The method builds the provenance chain for the given
    record_id (using the same logic as walk_chain), then lays it out as a
    tree and renders it to PNG, PDF, or another format depending on
    output_path extension.

    Args:
        record_id: The record to root the tree at (e.g. outcome id or "last").
        run_id: Run identifier (same as the run's output folder name).
        output_path: Path for the output file (e.g. chain.png, chain.pdf).
        output_base: Base directory for run folders; default "./output".

    Raises:
        FileNotFoundError: If run metadata or records are not found.
        ValueError: If record_id is "last" but the run has no outcomes, or if
            record_id is not in the run. ImportError if matplotlib is not installed.
    """
    resolved = resolve_run(run_id, output_base=output_base)
    index = _build_index(resolved)
    effective_id = record_id
    if record_id == "last":
        effective_id = _find_last_outcome(index)
        if effective_id is None:
            raise ValueError("No outcome records found in run; cannot resolve 'last'")
    elif record_id != "initial_state" and effective_id not in index:
        raise ValueError(f"Record {record_id!r} not found in run")

    nodes: List[tuple] = []
    edges: List[tuple] = []
    _collect_nodes_edges(effective_id, index, 20, 0, set(), nodes, edges)

    if not nodes:
        return

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError("render_chain_tree requires matplotlib") from e

    from collections import defaultdict
    depth_groups: Dict[int, List[int]] = defaultdict(list)
    for i, (_, _, d) in enumerate(nodes):
        depth_groups[d].append(i)
    node_id_to_idx = {nid: i for i, (nid, _, _) in enumerate(nodes)}
    pos: Dict[int, tuple] = {}
    max_d = max(d for _, _, d in nodes)
    for d, idxs in depth_groups.items():
        x = -d
        for j, idx in enumerate(idxs):
            spread = len(idxs)
            y = (j - (spread - 1) / 2) * 1.8
            pos[idx] = (x, y)

    xs = [pos[i][0] for i in range(len(nodes))]
    ys = [pos[i][1] for i in range(len(nodes))]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    pad_x = max(1.5, (x_max - x_min) * 0.15) if x_max != x_min else 1.5
    pad_y = max(1.0, (y_max - y_min) * 0.15) if y_max != y_min else 1.0
    x_lo, x_hi = x_min - pad_x, x_max + pad_x
    y_lo, y_hi = y_min - pad_y, y_max + pad_y

    w = max(6, min(14, (x_hi - x_lo) * 0.8))
    h = max(4, min(10, (y_hi - y_lo) * 0.8))
    fig, ax = plt.subplots(figsize=(w, h))
    kind_colors = {"outcome": "#87ceeb", "agent_update": "#90EE90", "trace": "#FFD700", "initial_state": "#333333"}
    for i, (nid, label, depth) in enumerate(nodes):
        x, y = pos[i]
        rec = index.get(nid)
        kind = rec.get("kind", "initial_state") if rec else "initial_state"
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
    ax.set_title("Provenance Chain — Why Did This State Happen?", fontsize=11, fontweight="bold")
    ax.axis("off")
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.set_aspect("equal")
    fig.tight_layout(pad=1.0)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ext = path.suffix.lower()
    if ext == ".png":
        fig.savefig(path, dpi=200, bbox_inches="tight")
    elif ext == ".pdf":
        fig.savefig(path, bbox_inches="tight")
    else:
        fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
