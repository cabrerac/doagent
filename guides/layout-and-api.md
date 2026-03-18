# Project layout and API

## Layout

```
doagent/          Library: Session, adapters, topology, records, participation
  core/
  analysis/
  records/
  interface/
examples/         gridworld_demo, push_demo, minimal_usage, README (config)
notebooks/        Colab step-by-step demos
guides/           doa-principles + layout-and-api (README has the env checklist)
experiments/      Comparison runners, baselines
docs/             Architecture / adapter notes for contributors
tests/
```

## API (what to import)

| Import | Role |
|--------|------|
| `doagent.Session` | `Session.from_config(config)`; `wrap_env`, `create_agents`, `inspect`, `visible_records`, `participation_registry` |
| `doagent.RunConfig` | Logging level; usually embedded in config dict |
| `doagent.make_env` | `make_env(factory, **kwargs)` for config-driven envs |
| `doagent.RunReporter` | Optional progress/summary helper in demos |

Config drives `shared_data`, `topology`, `policies`, `participation`. For `ParticipationRecord` only: `from doagent.core import ParticipationRecord`.

Do not rely on `doagent.core` or `doagent.records` for general app code beyond participation records.
