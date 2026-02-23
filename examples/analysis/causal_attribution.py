"""Causal attribution analysis -- per-agent contribution derived from trace records.

Uses the trace graph to attribute state transitions (and the discoveries they
represent) to individual agents. Produces:

1. Per-agent cumulative coverage over time (line chart)
2. Total cells discovered per agent (bar chart)
3. Decision effectiveness: productive vs redundant moves per agent
4. Console summary table

Usage:
    python causal_attribution.py <records_dir> [--output-dir <dir>]

Example:
    python causal_attribution.py output/gridworld_run_20260221_022506/records
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


ACTION_NAMES = {0: "stay", 1: "left", 2: "right", 3: "up", 4: "down"}


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def extract_agent_cells(outcome: Dict[str, Any], agent: str) -> Set[Tuple[int, int]]:
    """Extract the set of observed cells for a specific agent from an outcome."""
    obs = outcome["payload"].get("observations", {})
    ob = obs.get(agent, {})
    return {(c["x"], c["y"]) for c in ob.get("cells", [])}


def extract_all_cells(outcome: Dict[str, Any]) -> Set[Tuple[int, int]]:
    """Extract the union of all observed cells across all agents."""
    obs = outcome["payload"].get("observations", {})
    cells: Set[Tuple[int, int]] = set()
    for ob in obs.values():
        cells.update((c["x"], c["y"]) for c in ob.get("cells", []))
    return cells


def compute_attribution(
    traces: List[Dict[str, Any]],
    outcomes: List[Dict[str, Any]],
    agent_updates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute per-agent causal attribution from traces.

    For each trace edge, attributes the new cells visible in the enabling
    agent's own observation (in the destination outcome) that were not visible
    in that agent's observation in the source outcome. This correctly
    distributes credit when multiple agents transition to the same state.
    """
    outcome_by_id = {r["id"]: r for r in outcomes}

    traces_sorted = sorted(traces, key=lambda t: t["payload"].get("round", 0))

    global_known: Set[Tuple[int, int]] = set()
    agent_discovered: Dict[str, Set[Tuple[int, int]]] = defaultdict(set)
    agent_productive: Dict[str, int] = defaultdict(int)
    agent_redundant: Dict[str, int] = defaultdict(int)

    per_round_cumulative: Dict[int, Dict[str, int]] = {}
    cumulative_by_agent: Dict[str, int] = defaultdict(int)
    max_round = 0

    current_round = 0
    round_new_cells: Set[Tuple[int, int]] = set()

    for trace in traces_sorted:
        payload = trace["payload"]
        from_id = payload.get("from_id", "")
        to_id = payload.get("to_id", "")
        agent = trace.get("actor", "unknown")
        rnd = payload.get("round", 0)
        max_round = max(max_round, rnd)

        if rnd != current_round:
            global_known.update(round_new_cells)
            if current_round > 0:
                per_round_cumulative[current_round] = dict(cumulative_by_agent)
            round_new_cells = set()
            current_round = rnd

        to_outcome = outcome_by_id.get(to_id)
        if to_outcome is None:
            continue

        agent_to_cells = extract_agent_cells(to_outcome, agent)

        agent_from_cells: Set[Tuple[int, int]] = set()
        if from_id != "initial_state":
            from_outcome = outcome_by_id.get(from_id)
            if from_outcome:
                agent_from_cells = extract_agent_cells(from_outcome, agent)

        agent_new_cells = agent_to_cells - agent_from_cells

        if agent_new_cells:
            agent_productive[agent] += 1
            globally_new = agent_new_cells - global_known - round_new_cells
            if globally_new:
                agent_discovered[agent].update(globally_new)
                round_new_cells.update(globally_new)
                cumulative_by_agent[agent] = len(agent_discovered[agent])
        else:
            agent_redundant[agent] += 1

    global_known.update(round_new_cells)
    if current_round > 0:
        per_round_cumulative[current_round] = dict(cumulative_by_agent)

    agents = sorted(set(
        list(agent_discovered.keys()) +
        list(agent_productive.keys()) +
        list(agent_redundant.keys())
    ))

    return {
        "agents": agents,
        "agent_discovered": {a: agent_discovered[a] for a in agents},
        "agent_productive": {a: agent_productive[a] for a in agents},
        "agent_redundant": {a: agent_redundant[a] for a in agents},
        "per_round_cumulative": dict(per_round_cumulative),
        "global_known": global_known,
        "max_round": max_round,
    }


def print_summary(attribution: Dict[str, Any]) -> None:
    agents = attribution["agents"]
    discovered = attribution["agent_discovered"]
    productive = attribution["agent_productive"]
    redundant = attribution["agent_redundant"]
    total_known = len(attribution["global_known"])

    print(f"\n{'='*70}")
    print("CAUSAL ATTRIBUTION ANALYSIS")
    print(f"{'='*70}")
    print(f"  Total unique cells discovered (via traces): {total_known}")
    print(f"  Rounds analyzed: {attribution['max_round']}")
    print()

    header = f"  {'Agent':<12} {'Discovered':>12} {'Productive':>12} {'Redundant':>12} {'Effectiveness':>14}"
    print(header)
    print(f"  {'-'*62}")

    for agent in agents:
        d = len(discovered.get(agent, set()))
        p = productive.get(agent, 0)
        r = redundant.get(agent, 0)
        total_moves = p + r
        eff = f"{p / total_moves * 100:.1f}%" if total_moves > 0 else "N/A"
        pct = f"({d / total_known * 100:.1f}%)" if total_known > 0 else ""
        print(f"  {agent:<12} {d:>8} {pct:>3} {p:>12} {r:>12} {eff:>14}")

    print(f"  {'-'*62}")
    total_d = sum(len(v) for v in discovered.values())
    total_p = sum(productive.values())
    total_r = sum(redundant.values())
    total_eff = f"{total_p / (total_p + total_r) * 100:.1f}%" if (total_p + total_r) > 0 else "N/A"
    print(f"  {'TOTAL':<12} {total_d:>12} {total_p:>12} {total_r:>12} {total_eff:>14}")
    print(f"{'='*70}\n")


def _load_agent_policies(output_dir: Path) -> Dict[str, str]:
    """Load agent_id -> policy_name from agent_policies.json if present."""
    path = output_dir / "agent_policies.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def render_charts(attribution: Dict[str, Any], output_dir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    agents = attribution["agents"]
    discovered = attribution["agent_discovered"]
    productive = attribution["agent_productive"]
    redundant = attribution["agent_redundant"]
    per_round_cumulative = attribution["per_round_cumulative"]
    max_round = attribution["max_round"]

    agent_labels_map = _load_agent_policies(output_dir)
    agent_display = [f"{a} ({agent_labels_map[a]})" if a in agent_labels_map else a for a in agents]

    AGENT_COLORS = {
        "agent_0": "#1f77b4",
        "agent_1": "#ff7f0e",
        "agent_2": "#2ca02c",
        "agent_3": "#d62728",
    }

    FONT_TITLE = 14
    FONT_AXIS = 12
    FONT_TICK = 11
    FONT_LEGEND = 10

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))

    # --- Chart 1: Cumulative coverage over time per agent ---
    ax1 = axes[0]
    rounds = sorted(per_round_cumulative.keys())
    running = {a: [] for a in agents}
    for a in agents:
        cum = 0
        for rnd in range(1, max_round + 1):
            snap = per_round_cumulative.get(rnd, {})
            cum = snap.get(a, cum)
            running[a].append(cum)

    x_rounds = list(range(1, max_round + 1))
    for agent in agents:
        color = AGENT_COLORS.get(agent, "#999999")
        label = agent_display[agents.index(agent)]
        ax1.plot(x_rounds, running[agent], label=label, color=color, linewidth=2)

    ax1.set_xlabel("Round", fontsize=FONT_AXIS)
    ax1.set_ylabel("Cumulative cells discovered", fontsize=FONT_AXIS)
    ax1.set_title("Per-Agent Cumulative Discovery", fontsize=FONT_TITLE, fontweight="bold")
    ax1.legend(fontsize=FONT_LEGEND)
    ax1.tick_params(axis="both", labelsize=FONT_TICK)
    ax1.grid(True, alpha=0.3)

    # --- Chart 2: Total cells discovered per agent (bar chart) ---
    ax2 = axes[1]
    counts = [len(discovered.get(a, set())) for a in agents]
    colors = [AGENT_COLORS.get(a, "#999999") for a in agents]
    bars = ax2.bar(agent_display, counts, color=colors, edgecolor="#444", linewidth=0.5)
    for bar, count in zip(bars, counts):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 str(count), ha="center", va="bottom", fontsize=FONT_TICK, fontweight="bold")
    ax2.set_ylabel("Cells discovered", fontsize=FONT_AXIS)
    ax2.set_title("Causal Attribution: Total Discovery", fontsize=FONT_TITLE, fontweight="bold")
    ax2.tick_params(axis="x", labelsize=FONT_TICK, rotation=15)
    ax2.tick_params(axis="y", labelsize=FONT_TICK)
    ax2.grid(True, alpha=0.3, axis="y")

    # --- Chart 3: Decision effectiveness (stacked bar) ---
    ax3 = axes[2]
    prod_vals = [productive.get(a, 0) for a in agents]
    red_vals = [redundant.get(a, 0) for a in agents]
    x = range(len(agents))
    ax3.bar(agent_display, prod_vals, label="Productive", color="#2ca02c", edgecolor="#444", linewidth=0.5)
    ax3.bar(agent_display, red_vals, bottom=prod_vals, label="Redundant", color="#d62728", edgecolor="#444", linewidth=0.5)

    for i, (p, r) in enumerate(zip(prod_vals, red_vals)):
        total = p + r
        if total > 0:
            eff = f"{p / total * 100:.0f}%"
            ax3.text(i, total + 0.3, eff, ha="center", va="bottom", fontsize=FONT_TICK, fontweight="bold")

    ax3.set_ylabel("Number of transitions", fontsize=FONT_AXIS)
    ax3.set_title("Decision Effectiveness", fontsize=FONT_TITLE, fontweight="bold")
    ax3.legend(fontsize=FONT_LEGEND)
    ax3.tick_params(axis="x", labelsize=FONT_TICK, rotation=15)
    ax3.tick_params(axis="y", labelsize=FONT_TICK)
    ax3.grid(True, alpha=0.3, axis="y")

    fig.suptitle("DOAgent Causal Attribution Analysis", fontsize=16, fontweight="bold", y=1.02)
    fig.tight_layout()

    png_path = output_dir / "causal_attribution.png"
    pdf_path = output_dir / "causal_attribution.pdf"
    fig.savefig(png_path, dpi=200, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Charts saved to {png_path} and {pdf_path}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python causal_attribution.py <records_dir> [--output-dir <dir>]")
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

    attribution = compute_attribution(traces, outcomes, agent_updates)
    print_summary(attribution)
    render_charts(attribution, output_dir)


if __name__ == "__main__":
    main()
