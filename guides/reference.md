# API reference and project layout

## Primary API

What user code should import (tests, demos, and experiments use only this surface):

| Import                | Purpose                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------ |
| `doagent.Session`     | Create session via `Session.from_config(config)`; wrap env, create agents, inspect records |
| `doagent.RunConfig`   | Logging level configuration (0, 1, or 2); can be part of config dict                       |
| `doagent.make_env`    | Build an environment from config (when using config-driven env)                            |
| `doagent.RunReporter` | Optional helper for run progress and final summary (e.g. in demos)                         |

Adapter, topology, and policies are configured via the config dict passed to `Session.from_config` (e.g. `shared_data.type`: `"memory"` | `"file"` | `"mongo"` | `"noop"`; `topology.mode`; `policies`; `participation`). Do not import `doagent.core` or `doagent.records` in user-facing code.

**Participation / openness:** `from doagent.core import ParticipationRecord` when registering participants (see [DOA principles — Openness](doa-principles.md#openness)).

**Demos** — end-to-end examples: see [Getting started — Run the demos](getting-started.md#run-the-demos).

## Project layout

```
doagent/             Library implementation
  core/              Session API, adapters, topology, record writing, participation
  analysis/          run_id-based analysis (provenance, traceability, accountability, interpretability)
  records/           Record types (SimpleRecord, provenance, accountability)
  interface/         Abstract adapter contracts
experiments/         Comparison runners (baseline vs file, topology comparison), reporters, baselines
examples/
  gridworld_demo/    File-backed gridworld run + analysis showcase
  push_demo/         File-backed push scenario (PettingZoo) + analysis showcase
  minimal_usage.py   Minimal Session API example
  README.md          Config options and how to run examples vs experiments
guides/              User-facing guides (this folder)
docs/                Contributor / architecture notes (adapter contract, data model, library boundaries)
tests/               Test suite
```
