---
author: "Christian Cabrera"
created: "2026-02-05"
id: "0010"
last_updated: "2026-02-11"
status: "In Progress"
compressed: false
related_requirements:
- "0010"
related_cips: []
tags:
- cip
- validation
- games
title: "Validation on Multi-Agent Games"
---

# CIP-0010: Validation on Multi-Agent Games

> **Note**: CIPs describe HOW to achieve requirements (WHAT).
> Use `related_requirements` to link to the requirements this CIP implements.

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [x] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented (add reason, use superseded_by if replaced)
- [ ] Deferred - Postponed (use blocked_by field to indicate blocker)

## Summary
Validate DOAgent on a representative multi-agent game that exercises coordination, shared data, and interpretability/traceability outputs.

## Motivation
Multi-agent games are canonical benchmarks for coordination. A toy game example provides an end-to-end validation of the current architecture with reproducible inputs and outputs.

## Detailed Description
Iteration 1 focuses on the PettingZoo MPE simple_push_v3 scenario that produces decision, explanation, trace, provenance, accountability, and outcome records. The same scenario should run against both in-memory and file-backed shared data adapters, using a minimal Gym/MARL dependency. We also include a baseline run that disables data-oriented writes to estimate overhead.

The simple push environment has 1 good agent, 1 adversary, and 1 landmark. The good agent is rewarded based on the distance to the landmark. The adversary is rewarded if it is close to the landmark, and if the good agent is far from the landmark (the difference of the distances). Thus the adversary must learn to push the good agent away from the landmark.

Options considered:
- **Option A**: Use a full external traffic simulator (higher fidelity, heavier dependency).
- **Option B**: Use a minimal Gym/MARL benchmark environment with a lightweight dependency.

We select **Option B** for the PoC.

Key points:
- Multi-round simulation with seeded randomness for reproducibility.
- Shared data records capture decisions, explanations, traces, provenance, accountability, and outcomes.
- Policy callables map directly to the `DecisionAgent`/`FunctionAgent` decision function so policies are reusable across scenarios (REQ-0011/0012).
- Tests validate both InMemorySharedData and FileSharedData adapters.
- Baseline mode runs the same policies and environment without shared-data writes for overhead comparison.

## Iteration Deliverable (PoC)
- Simple push validation example using a minimal Gym/MARL dependency.
- Policy registry/config that assigns reusable policies to agents (maps to FunctionAgent).
- End-to-end tests for in-memory and file adapters.
- Baseline run for overhead comparison (no data-oriented writes).
- README section documenting the validation example.

## Iteration 2 Extension (Grid-World Communication)
Iteration 2 adds a lightweight grid-world mapping scenario to validate agent-to-agent communication via the shared data model, plus decentralisation and open participation.

Goals:
- Agents publish and consume shared data records during each round (shared data as a medium, not just a world log).
- Partial observations; agents collaborate to build a map or discover landmarks.
- Topology modes change information flow (centralised vs federated vs peer-to-peer).
- Agents can join/leave mid-run; registry updates affect available resources.

Candidate policies:
- Frontier exploration (greedy coverage of unknown cells).
- Random walk baseline (biased toward unexplored cells).
- Auction-based task allocation (centralised or P2P bidding for frontiers).

Key outputs:
- Shared-data messages are traceable back to decisions and map outcomes.
- Metrics include map coverage, discovery time, and per-agent contributions.

## Implementation Plan
1. **Define scenario and policy interface**
   - Select the simple_push_v3 environment and rounds/seed settings.
   - Define a reusable policy interface that maps to the decision function used by FunctionAgent.
2. **Implement example**
   - Run multi-round simulation, write decision/explanation/trace/outcome records with provenance and accountability.
3. **Add tests**
   - Verify record counts, provenance/accountability presence, and trace links for both adapters.
4. **Add baseline comparison**
   - Run the same scenario with data-oriented writes disabled and collect timing/size metrics.
5. **Document usage**
   - README section with run command, expected outputs, and scenario description.

## Iteration 2 Plan (Grid-World Communication)
1. **Define environment + shared data flow**
   - Grid size, partial observation radius, map update payloads.
   - Specify how shared data is consumed (centralised hub or agent-local reads).
2. **Implement policies**
   - Frontier explorer, random baseline, optional auction allocator.
3. **Support topology + open participation**
   - Join/leave events and registry updates during a run.
   - Topology-driven visibility and routing.
4. **Add tests + metrics**
   - Coverage, discovery time, and per-agent contributions.
5. **Add graphical interfac**
   - Render the grid-world game to show how the agents operate.
6. **Document usage**
   - Example run + plots/CSV for the new scenario.

## Configuration Schema (Draft)
The validation runner should accept a minimal config that specifies environment settings and per-agent policy assignment. This keeps policy selection reusable across scenarios.

```yaml
run:
  id: "push-demo-001"
  seed: 123
  rounds: 5
  deterministic: true

adapters:
  - type: "in_memory"
  - type: "file"
    params:
      path: "output/push_records.jsonl"

output:
  base_dir: "output/push_demo"
  records_path: "output/push_demo/records.jsonl"
  summary_path: "output/push_demo/summary.json"
  metrics_path: "output/push_demo/metrics.json"

logging:
  level: "INFO"
  console: true
  file: "output/push_demo/run.log"
  log_records: true

scenario:
  name: "simple_push"
  env:
    name: "pettingzoo:mpe2:simple_push_v3"
    params:
      max_cycles: 25
      continuous_actions: false
      dynamic_rescaling: false
  interpretability: "default"
  traceability: "default"
  provenance: "default"
  accountability: "default"

agents:
  - id: "adversary_0"
    policy:
      name: "epsilon_greedy"
      params:
        epsilon: 0.2
        decay: 0.99
        min_epsilon: 0.05
  - id: "agent_0"
    policy:
      name: "fixed"
      params:
        action: 0

metrics:
  track:
    - "good_distance_to_landmark"
    - "adversary_distance_to_landmark"
    - "distance_gap"
  aggregation: "mean"
```

## Backward Compatibility
Additive only; no breaking changes. Iteration 2 work must fit the current architecture; if new components are introduced, they must interoperate with existing adapters, records, and scenarios.

## Testing Strategy
- Unit test executes the scenario for InMemorySharedData and FileSharedData.
- Assertions verify default interpretability, traceability, provenance, and accountability artefacts exist.
- Baseline run records timing/size metrics for comparison (no assertions on absolute values).

## Related Requirements
This CIP addresses the following requirements:
- REQ-0010: Validation on Multi-Agent Games

## Implementation Status
- [x] Define toy game scenario
- [x] Implement example
- [x] Add tests for both adapters
- [x] Document usage
- [x] Define grid-world environment + shared-data flow
- [x] Implement grid-world policies
- [x] Add topology + open participation hooks
- [x] Add tests + metrics for grid-world scenario
- [x] Add graphical interface for grid-world (ANSI + pygame)
- [x] Document grid-world usage

## Project Layout

### Validation module structure
Scenario-specific code is grouped by scenario; shared helpers remain at the top level:

```
doagent/validation/
├── baseline.py
├── environment.py
├── policy.py
├── reporting.py
├── multiprocess_interface.py
├── push/
│   ├── envs.py
│   ├── agents.py
│   └── scenario.py
└── gridworld/
    ├── env.py
    ├── agents.py
    ├── policies.py
    └── scenario.py
```

### Examples layout
Examples are grouped by scenario and library feature:

```
examples/
├── validation/
│   ├── push/
│   │   └── push_validation.py
│   ├── gridworld/
│   │   ├── gridworld_validation.py
│   │   └── gridworld_validation_config.yaml
│   └── plot_validation_metrics.py
└── features/
    ├── minimal_usage.py
    ├── model_agnostic_agent.py
    ├── interpretability_usage.py
    ├── traceability_usage.py
    ├── provenance_usage.py
    └── accountability_usage.py
```

### Output layout
Run outputs use a consistent layout for both push and grid-world:

```
output/<scenario>_run_YYYYMMDD_HHMMSS/
├── <scenario>_validation_summary.json   # in run folder root
├── plots/                               # PDF and PNG
│   ├── reward_series.pdf, .png
│   ├── action_counts.pdf, .png
│   ├── action_entropy.pdf, .png
│   └── gridworld_contributions.pdf, .png  (grid-world only)
└── metrics/                             # CSV files
    ├── reward_series.csv
    ├── action_counts.csv
    ├── action_entropy.csv
    └── gridworld_metrics.csv            (grid-world only)
```

## Progress Updates

### 2026-02-05
Task accepted; implementation not started yet. Proceed via the five-step internal workflow.

### 2026-02-06
Reflection (Iteration 1):
- Achieved an end-to-end external validation scenario (simple_push_v3) with decisions, explanations, traces, provenance, accountability, and outcomes across multiple rounds.
- Validation highlights gaps: interpretability remains shallow, traceability is limited to short chains, provenance lacks environment context, and accountability metadata is static.
- The record pipeline behaves more like a world log than a shared data medium between agents; future iterations should include environments where agents read and communicate via shared data.
- The scenario does not exercise decentralisation or open participation; these remain unvalidated and should be addressed with future environments.
- Metrics tooling (baseline, reward series, entropy, plots/CSVs) enables clearer behaviour comparisons, but reward scales are not comparable across agents.

### 2026-02-09
Iteration 2 kickoff:
- Confirmed the grid-world communication scenario and its stages (environment, policies, topology/participation, tests/metrics, UI, docs).
- All Iteration 2 changes must fit the current architecture; any new components must interoperate with existing records, adapters, and scenarios.

### 2026-02-10
Iteration 2 progress:
- Implemented grid-world environment, agents, and scenario with shared-data communication using `agent_update` records.
- Added logical decentralisation with topology-driven visibility (centralised, federated, peer-to-peer).
- Added multiprocessing option with a `MultiProcessInterface` bridge for persisted adapters.
- Added grid-world policy factories (random explore, frontier explore, auction stub).
- Implemented stochastic join/leave via energy model with participation registry updates.
- Added grid-world tests and metrics summary output.
- Added grid-world rendering (ANSI/pygame); documentation still pending.

### 2026-02-11
Iteration 2 progress:
- Extended RunReporter to attach extra metrics.
- Added grid-world run metrics to summary and plotting/CSV support.
- Restructured validation module: scenario-specific code in `push/` and `gridworld/` subpackages; shared components (baseline, environment, policy, reporting, multiprocess_interface) at top level.
- Standardised output layout: summary in run root; plots in `plots/`; metrics CSV in `metrics/`.
- All validation backlog tasks completed.

## References
- None yet
