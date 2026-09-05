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
| `doagent.Session` | `Session.from_config(config)`; `wrap_env`, `create_agents`, `inspect`, `visible_records`, `decision_context`, `visible_participants`, `register_participant`, `deregister_participant` |
| `doagent.RunConfig` | Logging level; usually embedded in config dict |
| `doagent.make_env` | `make_env(factory, **kwargs)` for config-driven envs |
| `doagent.RunReporter` | Optional progress/summary helper in demos |
| `doagent.core.topology` | Optional built-in hooks: `mesh_on_membership_change`, `relay_join_leave_as_hub`, `snapshot_hub_roster` |

**Session methods (decision time):**

- `visible_records(agent_id, kind=...)` — records this agent may read (topology filter).
- `decision_context(agent_id, kinds=..., last_n=..., summarise=...)` — same visibility, then optional kind(s), last N, and your summarise function.
- `visible_participants(agent_id)` — who is in, from this agent’s filtered `participation` records.
- `register_participant` / `deregister_participant` — update the live registry **and** append a `participation` record.

Config drives `shared_data`, `topology` (`mode`, optional `visibility`, `on_membership_change`, `on_hub_membership`), `policies`, `participation`. How to use them: [`guides/doa-principles.md`](doa-principles.md).

For a run, prefer Session. Use `doagent.core.topology` only for the optional hook functions. Do not import record helpers or adapters from `doagent.core` in app code.
