# DOAgent Analysis & Visualization Tools

Scripts for analyzing and visualizing the records produced by DOAgent runs.
These demonstrate **interpretability**, **traceability**, **provenance**, and
**causal attribution** — all derived from the shared data model, with no
access to agent internals.

## Prerequisites

```bash
pip install networkx matplotlib pyyaml
```

All scripts expect a `records/` directory containing JSONL files produced by a
DOAgent run at logging level 2 (`trace.jsonl`, `outcome.jsonl`,
`agent_update.jsonl`).

## Scripts

### 1. Trace Graph Visualization (`trace_graph.py`)

Builds a directed state-transition graph from trace records and renders it as
an image. Nodes are outcome states, edges are trace links colored by the agent
whose decision enabled the transition.

```bash
python trace_graph.py <records_dir> [--output-dir <dir>]
```

**Outputs**: `trace_graph.png`, `trace_graph.pdf`, `trace_graph.dot`

**Demonstrates**: Traceability (linked state changes), state deduplication
(convergence points), provenance (edge attribution).

### 2. Provenance Chain Walker (`provenance_walker.py`)

Walks backwards from any record (or the final outcome) through the full
provenance chain, showing how each state was derived from agent decisions and
prior states.

```bash
python provenance_walker.py <records_dir> [<record_id> | last] [--depth <n>]
```

**Outputs**: Console text tree + `provenance_tree.png`, `provenance_tree.pdf`

**Demonstrates**: Interpretability (human-readable decision trail), provenance
(full attribution from output to inputs).

### 3. Causal Attribution Analysis (`causal_attribution.py`)

Computes per-agent causal contribution by analyzing which agent's decisions
led to the discovery of new cells, using trace edges rather than raw
observations.

```bash
python causal_attribution.py <records_dir> [--output-dir <dir>]
```

**Outputs**: `causal_attribution.png`, `causal_attribution.pdf` with 3 charts:
cumulative discovery over time, total discovery bar chart, decision
effectiveness (productive vs redundant moves).

**Demonstrates**: Causal reasoning from the trace graph, accountability (who
contributed what), data-oriented analysis.

### 4. Topology Comparison (`topology_comparison.py`)

Runs the gridworld under 3 coordination topologies (centralised, peer-to-peer,
federated) with the same seed, then produces a side-by-side comparison.

```bash
# Run all three topologies
python topology_comparison.py --run [--output-dir <dir>]

# Or analyze existing output directories
python topology_comparison.py --dirs <cent_recs> <p2p_recs> <fed_recs>
```

**Outputs**: `topology_comparison.png`, `topology_comparison.pdf` with 4
charts comparing graph structure, total coverage, per-agent discovery, and
decision effectiveness across topologies.

**Demonstrates**: How the same agents with different coordination produce
different trace graphs and outcomes — all visible through the traceability
infrastructure.

## Presentation Flow

1. **"What does DOAgent record?"** — show logging levels (0/1/2), record kinds
2. **Trace graph** — "every decision and state change is linked" (visual graph)
3. **Zoom into one transition** — provenance walker output showing the full chain
4. **Causal attribution** — "who contributed what, and we can prove it from data"
5. **Topology comparison** — same agents, different coordination, different traces

## Configuration

Topology comparison configs are in `configs/`:
- `centralised.yaml` — all agents see all records
- `peer_to_peer.yaml` — ring visibility (each agent sees one neighbour)
- `federated.yaml` — agents report to a hub that aggregates
