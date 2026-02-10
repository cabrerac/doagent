# DOAgent

Data‑Oriented Agents for accountable multi‑agent systems.

Agentic systems often lack interpretability, traceability, and accountability. DOAgent addresses this by making shared data the primary interface between agents.

DOAgent is a library for building [data‑oriented](https://dl.acm.org/doi/10.1145/3769292) multi‑agent systems with configurable coordination and transparent interaction [1].

**Goals**:
- Shared data model as the communication substrate.
- Support for decentralisation from centralised to federated and peer‑to‑peer agent orchestration.
- Open multi-agent systems architectures.
- Improved interpretability, traceability, provenance, and accountability.

## Quickstart

Use these commands to run the example and the tests.

```bash
pip install -r requirements.txt
python -m examples.minimal_usage
python -m unittest -v
```

## Project layout

DOAgent is powered by [VibeSafe](https://github.com/lawrennd/vibesafe). The project structure is as follows:

- `doagent/` — library implementation (core, records, interfaces)
- `examples/` — runnable examples
- `tests/` — test suite
- `cip/`, `requirements/`, `backlog/`, `tenets/` — project documentation and planning powered by [VibeSafe](https://github.com/lawrennd/vibesafe)

> **Status**: This project is in active development.
> To see the current status, run `./whats-next` (VibeSafe).

## Minimal API surface

The current public API used by the PoC includes:

- `doagent.core.InMemorySharedData` — in-memory shared data adapter
- `doagent.core.FileSharedData` — file-backed shared data adapter
- `doagent.core.StubAgent` — minimal agent adapter
- `doagent.core.FunctionAgent` — function-backed decision agent
- `doagent.core.new_record` — helper to create records
- `doagent.core.new_explanation_record` — helper to create explanation records
- `doagent.core.new_trace_record` — helper to create trace records
- `doagent.core.Topology` — coordination topology modes
- `doagent.core.TopologyConfig` — topology configuration
- `doagent.core.select_routing` — coordination hook stub
- `doagent.core.ParticipationRecord` — participation record
- `doagent.core.InMemoryParticipationRegistry` — in-memory participation registry
- `doagent.records.SimpleRecord` — record envelope type
- `doagent.records.DecisionRequest` — decision request payload
- `doagent.records.DecisionResponse` — decision response payload
- `doagent.records.ExplanationPayload` — interpretability payload
- `doagent.records.ExplanationRecord` — explanation record envelope
- `doagent.records.TracePayload` — trace payload
- `doagent.records.new_provenance` — helper to build provenance for records
- `doagent.records.Accountability` — accountability envelope type (owner, policy_id, responsibility_scope)
- `doagent.records.new_accountability` — helper to build accountability for records

## Minimal usage

The smallest example that writes and listens to shared data.

```python
from doagent.core import InMemorySharedData, StubAgent

shared_data = InMemorySharedData()
agent = StubAgent("agent-1", shared_data)

agent.write(kind="note", payload={"text": "Hello from DOAgent"})

for record in shared_data.listen("note"):
    print(record.id, record.kind, record.payload)
```

See `examples/minimal_usage.py` for a runnable example, or run it with:

```bash
python -m examples.minimal_usage
```

## Model-agnostic agent example

This section shows how to wrap a callable decision function.

```python
from doagent.core import FunctionAgent, InMemorySharedData

def decide_fn(request: dict) -> dict:
    return {"decision": {"action": "log", "message": request.get("goal")}}

shared_data = InMemorySharedData()
agent = FunctionAgent("agent-1", shared_data, decide_fn)

request = {"id": "req-1", "actor": "agent-1", "goal": "store a decision"}
response = agent.decide(request)

record = list(shared_data.listen("decision"))[0]
assert record.payload["response"]["id"] == response["id"]
```

Run the example with:

```bash
python -m examples.model_agnostic_agent
```

## Interpretability example

This section shows how to attach explanations to decision records.

```python
from doagent.core import InMemorySharedData, new_explanation_record, new_record

shared_data = InMemorySharedData()

decision = new_record(
    actor="agent-1",
    kind="decision",
    payload={"decision": {"action": "approve"}},
)
shared_data.write(decision)

explanation = new_explanation_record(
    actor="agent-1",
    decision_id=decision.id,
    summary="Approved due to policy compliance.",
    details="The request met all mandatory checks.",
    evidence=["policy-1"],
)
shared_data.write(explanation)

record = list(shared_data.listen("explanation"))[0]
assert record.payload["decision_id"] == decision.id
```

Run the example with:

```bash
python -m examples.interpretability_usage
```

## Traceability example

This section shows how to link records via trace edges.

```python
from doagent.core import InMemorySharedData, new_record, new_trace_record

shared_data = InMemorySharedData()

upstream = new_record(
    actor="agent-1",
    kind="note",
    payload={"text": "source"},
)
downstream = new_record(
    actor="agent-2",
    kind="decision",
    payload={"decision": {"action": "use"}},
)
shared_data.write(upstream)
shared_data.write(downstream)

trace = new_trace_record(
    actor="agent-2",
    from_id=upstream.id,
    to_id=downstream.id,
    relation="used",
    notes="Decision used upstream note.",
)
shared_data.write(trace)

record = list(shared_data.listen("trace"))[0]
assert record.payload["from_id"] == upstream.id
```

Run the example with:

```bash
python -m examples.traceability_usage
```

## Provenance example

Provenance records who created a record and what they used (sources, tools). Use `new_provenance` to build provenance for `new_record`. Trace sync from provenance (one trace edge per source) is planned for a later iteration.

```python
from doagent.core import InMemorySharedData, new_record
from doagent.records import new_provenance

shared_data = InMemorySharedData()

provenance = new_provenance(
    agent="agent-1",
    sources=["r1", "r2"],
    tools=["search"],
    notes="Created from upstream records.",
)
record = new_record(
    actor="agent-1",
    kind="decision",
    payload={"decision": {"action": "approve"}},
    provenance=provenance,
)
shared_data.write(record)

fetched = shared_data.read(record.id)
assert len(fetched.provenance["contributions"]) == 1
assert fetched.provenance["contributions"][0]["sources"] == ["r1", "r2"]
```

Run the example with:

```bash
python -m examples.provenance_usage
```

## Accountability example

Accountability attaches ownership and governance context to a record (owner, policy_id, responsibility_scope) so decisions can be reviewed and governed. Use `new_accountability` to build accountability for `new_record`.

```python
from doagent.core import InMemorySharedData, new_record
from doagent.records import new_accountability

shared_data = InMemorySharedData()

accountability = new_accountability(
    owner="team-a",
    policy_id="policy-001",
    responsibility_scope="decisions",
)
record = new_record(
    actor="agent-1",
    kind="decision",
    payload={"decision": {"action": "approve"}},
    accountability=accountability,
)
shared_data.write(record)

fetched = shared_data.read(record.id)
assert fetched.accountability["owner"] == "team-a"
assert fetched.accountability["policy_id"] == "policy-001"
```

Run the example with:

```bash
python -m examples.accountability_usage
```

## Validation example (simple push)

This end-to-end validation runs a multi-round simple push scenario with policies, explanations, traces, and provenance. It exercises the shared data model and produces decision, explanation, trace, and outcome records plus run metrics.

The PettingZoo simple push environment has 1 good agent, 1 adversary, and 2 landmarks (one is randomly selected as the goal). The good agent is rewarded based on the distance to the goal landmark. The adversary is rewarded if it is close to the goal landmark, and if the good agent is far from the goal landmark (the difference of the distances). Thus the adversary must learn to push the good agent away from the goal.

```python
from doagent.validation import PolicyRegistry, PushAgentConfig, make_push_env, run_push_validation
from doagent.core import InMemorySharedData
from doagent.records import new_provenance

shared_data = InMemorySharedData()
env = make_push_env(
    "pettingzoo:mpe2:simple_push_v3",
    {"max_cycles": 25, "continuous_actions": False, "dynamic_rescaling": False},
)
registry = PolicyRegistry()

def fixed_policy(params):
    action = params.get("action", 0)
    def decide(request):
        return {"decision": {"action": action}}
    return decide

registry.register("fixed", fixed_policy)

configs = [
    PushAgentConfig(
        id="adversary_0",
        policy={"name": "fixed", "params": {"action": 0}},
        metadata={
            "explanation": "Hold position (noop) in push task.",
            "provenance": new_provenance(agent="adversary_0", sources=[]),
        },
    ),
]

summary = run_push_validation(
    shared_data=shared_data,
    env=env,
    registry=registry,
    configs=configs,
    rounds=2,
    seed=123,
)
print(summary.outcomes)
```

Run the example with:

```bash
pip install -r requirements.txt
python -m examples.push_validation
```

Plots and CSVs (requires matplotlib):

```bash
pip install matplotlib
python -m examples.plot_validation_metrics "output/push_run_YYYYMMDD_HHMMSS/push_validation_summary.json"
```

## Validation example (grid-world mapping)

This validation runs a dependency-free grid-world mapping scenario with partial observations and agent-to-agent communication via shared data. Agents publish `agent_update` records each round, consume the shared map, and decide movement actions. Topology modes control visibility (centralised, federated, peer-to-peer), and optional energy-based participation enables stochastic join/leave.

```python
from doagent.validation import (
    PolicyRegistry,
    GridAgentConfig,
    make_grid_env,
    register_gridworld_policies,
    run_gridworld_validation,
)
from doagent.core import (
    InMemorySharedData,
    InMemoryParticipationRegistry,
    Topology,
    TopologyConfig,
)

shared_data = InMemorySharedData()
participation = InMemoryParticipationRegistry()
registry = PolicyRegistry()
register_gridworld_policies(registry)

agent_ids = ["agent_0", "agent_1", "agent_2"]
env = make_grid_env(
    width=6,
    height=6,
    agent_ids=agent_ids,
    landmarks=2,
    observation_radius=1,
    max_cycles=25,
    seed=7,
)

configs = [
    GridAgentConfig(id="agent_0", policy={"name": "grid_frontier", "params": {}}),
    GridAgentConfig(id="agent_1", policy={"name": "grid_random", "params": {"seed": 1}}),
    GridAgentConfig(
        id="agent_2", policy={"name": "grid_auction_frontier", "params": {"seed": 2}}
    ),
]

summary = run_gridworld_validation(
    shared_data=shared_data,
    env=env,
    registry=registry,
    configs=configs,
    rounds=10,
    seed=123,
    topology=TopologyConfig(mode=Topology.PEER_TO_PEER),
    visibility={"agent_0": ["agent_1"], "agent_1": ["agent_2"]},
    participation_registry=participation,
    energy_model=True,
    energy_min=4,
    energy_max=10,
    energy_decay=1,
    energy_recharge=1,
    energy_leave_threshold=2,
)
print(summary.outcomes)
```

Example configuration (draft): `examples/gridworld_validation_config.yaml`.

## Topology example

This section shows how to select a topology and obtain a routing decision.

```python
from doagent.core import Topology, TopologyConfig, select_routing

config = TopologyConfig(mode=Topology.FEDERATED)
decision = select_routing(config)
```

## Participation example

This section shows how to register and query agent participation.

```python
from doagent.core import InMemoryParticipationRegistry, ParticipationRecord

registry = InMemoryParticipationRegistry()
registry.register(ParticipationRecord(agent_id="agent-1", capabilities=["compute"]))
record = registry.get("agent-1")
```

## References
[1] Christian Cabrera, Andrei Paleyes, Pierre Thodoroff, and Neil D. Lawrence. 2025. Machine Learning Systems: A Survey from a Data-Oriented Perspective. ACM Computing Surveys. [Available online](https://dl.acm.org/doi/10.1145/3769292)
