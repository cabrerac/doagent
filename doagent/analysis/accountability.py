"""Accountability analysis: causal attribution, who contributed what."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from ._resolve import resolve_run


def _extract_agent_cells(outcome: Any, agent: str) -> Set[Tuple[int, int]]:
    """Extract the set of observed cells (x, y) for a specific agent from an outcome record."""
    payload = getattr(outcome, "payload", outcome) if not isinstance(outcome, dict) else outcome.get("payload", {})
    obs = payload.get("observations", {}) if isinstance(payload, dict) else {}
    ob = obs.get(agent, {}) if isinstance(obs, dict) else {}
    cells = ob.get("cells", []) if isinstance(ob, dict) else []
    return {(c["x"], c["y"]) for c in cells if isinstance(c, dict) and "x" in c and "y" in c}


def _compute_attribution(
    traces: List[Any],
    outcomes: List[Any],
) -> Dict[str, Any]:
    """Compute per-agent causal attribution from traces and outcomes.

    For each trace edge, attributes new cells visible in the enabling agent's
    observation (destination outcome) that were not in that agent's observation
    in the source outcome. Tracks productive vs redundant moves per agent.
    """
    outcome_by_id = {o.id: o for o in outcomes}

    def trace_round(t: Any) -> int:
        p = t.payload if hasattr(t, "payload") else (t.get("payload", {}) if isinstance(t, dict) else {})
        return p.get("round", 0) if isinstance(p, dict) else 0

    def trace_actor(t: Any) -> str:
        return getattr(t, "actor", "unknown") if not isinstance(t, dict) else t.get("actor", "unknown")

    traces_sorted = sorted(traces, key=trace_round)

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
        payload = trace.payload if hasattr(trace, "payload") else (trace.get("payload", {}) if isinstance(trace, dict) else {})
        if not isinstance(payload, dict):
            continue
        from_id = payload.get("from_id", "")
        to_id = payload.get("to_id", "")
        agent = trace_actor(trace)
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

        agent_to_cells = _extract_agent_cells(to_outcome, agent)
        agent_from_cells: Set[Tuple[int, int]] = set()
        if from_id != "initial_state":
            from_outcome = outcome_by_id.get(from_id)
            if from_outcome:
                agent_from_cells = _extract_agent_cells(from_outcome, agent)

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


def causal_attribution(
    run_id: str,
    *,
    output_base: str = "./output",
    write_output: bool = False,
) -> Dict[str, Any]:
    """Attribute "who contributed what" to the run by assigning credit from trace edges.

    **What it means:** Causal attribution answers "who contributed what?" for a
    multi-agent run. Each transition in the trace graph is caused by one agent's
    decision. Attribution assigns the *effect* of that transition (e.g. newly
    discovered cells, or other outcome deltas) to that agent. It uses each
    agent's own observations so that when multiple agents could have led to the
    same state, only the agent who actually enabled the transition gets credit
    for the new discoveries visible in their observation. The result supports
    per-agent metrics: coverage over time, total contribution, and effectiveness
    (productive vs redundant moves).

    **How it works:** The method loads outcome, trace, and agent_update records
    for the run. For each trace edge, it identifies the enabling agent. From the
    destination outcome it takes that agent's observation (e.g. cells seen)
    and compares it to the source outcome's observation for the same agent to
    count what is new. It aggregates these counts per agent across rounds,
    producing a structured dict with per-agent discovery counts, cumulative
    coverage, and productive vs redundant decision counts. When write_output
    is True, writes attribution charts (PNG + PDF) to
    output_base/run_id/analysis/accountability/.

    Args:
        run_id: Run identifier (same as the run's output folder name).
        output_base: Base directory for run folders; default "./output".
        write_output: If True, write PNG and PDF to output_base/run_id/analysis/accountability/.

    Returns:
        A structured dict with keys: agents (list), agent_discovered (agent -> set
        of (x,y) cells), agent_productive, agent_redundant (agent -> int),
        per_round_cumulative (round -> agent -> cumulative count), global_known
        (set of (x,y)), max_round. Suitable for render_attribution_charts.

    Raises:
        FileNotFoundError: If run metadata or records are not found.
    """
    resolved = resolve_run(run_id, output_base=output_base)
    outcomes = list(resolved.inspect("outcome"))
    traces = list(resolved.inspect("trace"))
    attribution = _compute_attribution(traces, outcomes)
    if write_output:
        out_dir = Path(output_base) / run_id / "analysis" / "accountability"
        out_dir.mkdir(parents=True, exist_ok=True)
        render_attribution_charts(attribution, str(out_dir))
    return attribution


def render_attribution_charts(attribution: Dict[str, Any], output_path: str) -> None:
    """Produce charts that visualise the causal attribution (coverage, totals, effectiveness).

    **What it means:** Attribution charts turn the output of causal_attribution
    into visual form: e.g. a line chart of per-agent cumulative coverage over
    time, a bar chart of total cells discovered per agent, and an effectiveness
    chart comparing productive vs redundant decisions per agent. This makes it
    easy to compare agents and spot contribution patterns.

    **How it works:** The method takes the structured attribution dict returned
    by causal_attribution and generates a single multi-panel figure (three
    subplots). If output_path is a directory, writes causal_attribution.png
    (and .pdf) there; if it is a file path, writes that file (format from
    extension).

    Args:
        attribution: The structured dict returned by causal_attribution.
        output_path: Path for the output file or directory (e.g. charts/,
            or attribution.png).

    Raises:
        ImportError: If matplotlib is not installed.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError("render_attribution_charts requires matplotlib") from e

    agents = attribution.get("agents", [])
    if not agents:
        return

    discovered = attribution.get("agent_discovered", {})
    productive = attribution.get("agent_productive", {})
    redundant = attribution.get("agent_redundant", {})
    per_round_cumulative = attribution.get("per_round_cumulative", {})
    max_round = max(attribution.get("max_round", 0), 1)

    agent_colors = {"agent_0": "#1f77b4", "agent_1": "#ff7f0e", "agent_2": "#2ca02c", "agent_3": "#d62728"}
    font_title = 14
    font_axis = 12
    font_tick = 11
    font_legend = 10

    has_discovery = any(discovered.get(a) for a in agents)
    ylabel_cumulative = "Cumulative contribution" if not has_discovery else "Cumulative cells discovered"
    ylabel_total = "Contribution (transitions)" if not has_discovery else "Cells discovered"
    title_cumulative = "Per-Agent Cumulative Contribution" if not has_discovery else "Per-Agent Cumulative Discovery"
    title_total = "Total Contribution by Agent" if not has_discovery else "Causal Attribution: Total Discovery"

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5), constrained_layout=True)

    # Chart 1: Cumulative over time per agent
    ax1 = axes[0]
    running = {a: [] for a in agents}
    for a in agents:
        cum = 0
        for rnd in range(1, max_round + 1):
            snap = per_round_cumulative.get(rnd, {})
            cum = snap.get(a, cum)
            running[a].append(cum)
    x_rounds = list(range(1, max_round + 1))
    for agent in agents:
        color = agent_colors.get(agent, "#999999")
        ax1.plot(x_rounds, running[agent], label=agent, color=color, linewidth=2)
    ax1.set_xlabel("Round", fontsize=font_axis)
    ax1.set_ylabel(ylabel_cumulative, fontsize=font_axis)
    ax1.set_title(title_cumulative, fontsize=font_title, fontweight="bold")
    ax1.legend(fontsize=font_legend)
    ax1.tick_params(axis="both", labelsize=font_tick)
    ax1.grid(True, alpha=0.3)

    # Chart 2: Total per agent (bar chart)
    ax2 = axes[1]
    counts = [len(discovered.get(a, set())) for a in agents]
    colors = [agent_colors.get(a, "#999999") for a in agents]
    bars = ax2.bar(agents, counts, color=colors, edgecolor="#444", linewidth=0.5)
    for bar, count in zip(bars, counts):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 str(count), ha="center", va="bottom", fontsize=font_tick, fontweight="bold")
    ax2.set_ylabel(ylabel_total, fontsize=font_axis)
    ax2.set_title(title_total, fontsize=font_title, fontweight="bold")
    ax2.tick_params(axis="x", labelsize=font_tick, rotation=15)
    ax2.tick_params(axis="y", labelsize=font_tick)
    ax2.grid(True, alpha=0.3, axis="y")

    # Chart 3: Decision effectiveness (productive vs redundant transitions)
    ax3 = axes[2]
    prod_vals = [productive.get(a, 0) for a in agents]
    red_vals = [redundant.get(a, 0) for a in agents]
    ax3.bar(agents, prod_vals, label="Productive", color="#2ca02c", edgecolor="#444", linewidth=0.5)
    ax3.bar(agents, red_vals, bottom=prod_vals, label="Redundant", color="#d62728", edgecolor="#444", linewidth=0.5)
    for i, (p, r) in enumerate(zip(prod_vals, red_vals)):
        total = p + r
        if total > 0:
            eff = f"{p / total * 100:.0f}%"
            ax3.text(i, total + 0.3, eff, ha="center", va="bottom", fontsize=font_tick, fontweight="bold")
    ax3.set_ylabel("Number of transitions", fontsize=font_axis)
    ax3.set_title("Decision Effectiveness", fontsize=font_title, fontweight="bold")
    ax3.legend(fontsize=font_legend)
    ax3.tick_params(axis="x", labelsize=font_tick, rotation=15)
    ax3.tick_params(axis="y", labelsize=font_tick)
    ax3.grid(True, alpha=0.3, axis="y")

    fig.suptitle("DOAgent Causal Attribution Analysis", fontsize=16, fontweight="bold", y=1.02)

    path = Path(output_path)
    if path.suffix:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == ".png":
            fig.savefig(path, dpi=200, bbox_inches="tight")
        else:
            fig.savefig(path, bbox_inches="tight")
    else:
        path.mkdir(parents=True, exist_ok=True)
        fig.savefig(path / "causal_attribution.png", dpi=200, bbox_inches="tight")
        fig.savefig(path / "causal_attribution.pdf", bbox_inches="tight")
    plt.close(fig)
