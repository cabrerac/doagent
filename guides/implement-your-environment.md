# Implement your own environment

1. **Environment** — Provide a callable that returns an env-like object: `reset(seed)` → observations dict (per agent), `step(actions)` → next observations, rewards, dones. Or use `make_env(your_create_fn, **params)`.

2. **Config** — Build a dict with `shared_data` (e.g. `{"type": "file"}` or `{"type": "mongo", "uri": "mongodb://localhost:27017"}`; with `scenario_name` and `output_base` the library creates run_id and metadata), `run_config` (e.g. `logging_level: 2`), `topology`, `policies` (name → callable), and optionally `participation: True` for a participation registry.

3. **Session** — `session = Session.from_config(config)`. For file-backed runs with `scenario_name`, the library creates `output_base/<run_id>/`, `records/`, and `metadata.json`; use `session.run_id` and `session.run_path` after creation.

4. **Run loop** — `env = session.wrap_env(your_env, env_actor="your_env")`, `agents = session.create_agents(agent_configs, goal="…")`. Each round: get observations, call `agent.decide(obs, round_id, inputs={...})` for each agent, then `env.step(actions)`. Use `session.visible_records(agent_id, kind="agent_update")` if agents need shared context.

5. **Analysis** — For file-backed runs, use `doagent.analysis` with `run_id=session.run_id` and `output_base`; call each module with `write_output=True` to write into `output_base/<run_id>/analysis/<category>/`. See [Analysis](analysis.md) and [Run the demos](getting-started.md#run-the-demos).

Keep scenario logic and policies in your code; use only the public API (`Session`, `RunConfig`, `make_env`, `RunReporter`, `doagent.analysis`). See `examples/gridworld_demo` and `examples/push_demo` for full patterns.

Config alternatives (topology, storage, logging, participation): [`examples/README.md`](../examples/README.md).
