# After the demos: quick start and your own environment

Use this page after you have [run the demos](../README.md#run-the-demos) (notebooks or locally).

## Quick start

The Session API is the entry point. Config → session → wrap env → create agents → run your loop. Recording is automatic.

```python
from doagent import Session, make_env

config = {
    "shared_data": {"type": "memory"},
    "run_config": {"logging_level": 2},
    "topology": {"mode": "centralised"},
    "policies": {"explore": my_policy_callable},
}
session = Session.from_config(config)
env = session.wrap_env(my_env)
agents = session.create_agents(agent_configs, goal="explore")

observations = env.reset(seed=42)
for round_id in range(1, rounds + 1):
    actions = {}
    for agent_id, agent in agents.items():
        result = agent.decide(observations[agent_id], round_id)
        actions[agent_id] = result["action"]
    step = env.step(actions)
    observations = step["observations"]
```

After the loop: `session.inspect("agent_update")`, `session.inspect("trace")`, etc.

For **file-backed** runs add `scenario_name`, `output_base`, and `shared_data: {type: file}` so you get `session.run_id` and can run [Analysis](../README.md#analysis).

## Implement your own environment (checklist)

1. **Environment** — Callable returning an object with `reset(seed)` → per-agent observations dict, `step(actions)` → observations, rewards, terminations/done. Or `make_env(your_fn, **params)`.

2. **Config** — `shared_data` (memory / file + scenario_name + output_base / mongo), `run_config.logging_level`, `topology`, `policies`. Optional: `participation: True`.

3. **Session** — `Session.from_config(config)` → `session.run_id` / `session.run_path` when file-backed.

4. **Loop** — `session.wrap_env(env, env_actor="…")`, `session.create_agents(configs, goal="…")`. Each round: `agent.decide(obs, round_id, inputs={…})`, then `env.step(actions)`. Use `session.visible_records(agent_id, kind="agent_update")` for shared context.

5. **Analysis** — With file or mongo + `run_id`, call `doagent.analysis` modules with `write_output=True` (see main README Analysis).

Full patterns: `examples/gridworld_demo`, `examples/push_demo`. Config (topology, storage, participation): [`examples/README.md`](../examples/README.md).
