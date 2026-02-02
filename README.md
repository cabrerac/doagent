# DOAgent

Data‑Oriented Agents for accountable multi‑agent systems.

Agentic systems often lack interpretability, traceability, and accountability. DOAgent addresses this by making shared data the primary interface between agents.

DOAgent is a library for building [data‑oriented](https://dl.acm.org/doi/10.1145/3769292) multi‑agent systems with configurable coordination and transparent interaction [1].

**Goals**:
- Shared data model as the communication substrate.
- Support for decentralisation from centralised to federated and peer‑to‑peer agents orchestrationg.
- Open multi-agent systems architectures.
- Improved interpretability, traceability, provenance, and accountability.

## Quickstart

Use these commands to run the example and the tests.

```bash
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
- `doagent.core.new_record` — helper to create records
- `doagent.records.SimpleRecord` — record envelope type

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

## References
[1] Christian Cabrera, Andrei Paleyes, Pierre Thodoroff, and Neil D. Lawrence. 2025. Machine Learning Systems: A Survey from a Data-Oriented Perspective. ACM Computing Surveys. [Available online](https://dl.acm.org/doi/10.1145/3769292)
