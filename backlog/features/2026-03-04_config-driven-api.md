---
id: "2026-03-04_config-driven-api"
title: "Config-driven API: hide internals, no scenario-specific env factories"
status: "Done"
priority: "High"
created: "2026-03-04"
last_updated: "2026-03-09"
category: "features"
related_cips:
- "0001"
- "0002"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- api
- library-first
- session
---

# Task: Config-driven API - hide internals, no scenario-specific env factories

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Aligns with CIP-0001 (Library First) and CIP-0002 (Shared Data Model): single public surface, configuration over class instantiation.

## Description

Make the library environment-agnostic and configuration-driven so that users do not import or instantiate internal types. The Session remains the primary API; all wiring (shared data, topology, participation, policies, logging) is expressed as configuration. Users provide an environment instance; the library does not provide scenario-specific env factories.

**Concrete changes:**

1. **Generic make_env replaces scenario-specific factories.** Remove `make_push_env`, `make_grid_env`, and `register_gridworld_policies` from the library entirely (not just from public exports -- delete the implementations). Add a single generic `make_env(entry_point, **params)` in the library that accepts either a string ("module.path:callable") or a callable, resolves it, and calls it with params. Scenario-specific env creation code (e.g. PettingZoo push setup, GridWorldEnv construction) moves to example code. All examples use `make_env` with their own entry points.

2. **Config-driven wiring.** Shared data, topology, participation registry, run config (e.g. logging level) are specified as configuration (dict or YAML). The library builds the corresponding adapter instances internally. Users do not import `InMemorySharedData`, `FileSharedData`, `TopologyConfig`, `InMemoryParticipationRegistry`, etc. Re-export from top-level `doagent` only what is needed for the minimal "run from config" path, or expose a single entry point (e.g. `Session.from_config(config)`) that accepts a config dict and instantiates adapters internally.

3. **SimpleRecord internal.** Do not export `SimpleRecord` (or the record envelope type) from the public API. Records are an internal communication format; users consume "records" via adapter methods (e.g. `listen()`) with a documented shape (e.g. dict-like) without needing to reference the type.

4. **Policy registry and reporting as config.** Policy registration and reporting (e.g. RunReporter, measure_baseline) are not required as user-instantiated classes. Policies can be specified in config (e.g. entry_point + params); reporting can be a config option or omitted. The library constructs PolicyRegistry (or equivalent) internally when running from config.

5. **Examples.** Push and gridworld validation examples are updated to use the config-driven path. They do not import from `doagent.core` or `doagent.records`. They either (a) use a single "run from config" entry point and supply env in example code, or (b) use Session with a config dict only (no direct adapter construction). Both examples work with the same generic pattern; no scenario-specific env factories from the library.

## Alternatives Considered

### Scenario-specific vs generic env creation

- **Alternative A:** Keep make_push_env / make_grid_env as optional "reference" helpers. Rejected: they tie the library to specific scenarios and contradict "library enables any environment."
- **Alternative B (original):** No make_env at all; user passes env directly. Initially selected but revised: having a generic make_env improves consistency across examples and enables config-driven env creation from YAML.
- **Alternative C (revised, selected):** Remove all scenario-specific env factories (make_push_env, make_grid_env) from the library entirely. Replace with a single generic `make_env` in the library. Scenario-specific env creation code moves to example/user code.

### Generic make_env mechanism

- **Alternative A (string only):** `make_env("module.path:callable", **params)` -- library resolves string entry point, imports callable, calls with params. Pro: config-friendly (YAML). Con: string-based, runtime import errors.
- **Alternative B (callable only):** `make_env(factory_fn, **params)` -- library calls the callable directly. Pro: simple, type-safe. Con: not config-friendly; adds little value over calling the factory directly.
- **Alternative C (hybrid, selected):** `make_env(entry_point, **params)` where entry_point is either a string ("module:callable") or a callable. If string, resolve and call; if callable, call directly. Pro: supports both config-driven (YAML) and programmatic usage; one function for both paths. Con: dual contract needs clear docs.

**Selected:** Hybrid make_env (Alternative C). Rationale: fits the config-driven direction (YAML configs specify entry points as strings) while keeping programmatic usage simple (pass a callable). The library contains zero scenario-specific code; all env creation logic lives in example/user code.

### Policy registration mechanism

- **Alternative A (keep PolicyRegistry explicit):** Users import PolicyRegistry, create it, register callables, pass to session.create_agents. Pro: familiar pattern. Con: extra import, boilerplate, inconsistent with config-driven direction.
- **Alternative B (policies in config, selected):** Policies specified in the config dict as entry points (e.g. "policies": {"my_policy": "module:fn"}). Session.from_config resolves them and builds the registry internally. Users never import or see PolicyRegistry. Pro: consistent with make_env and Session.from_config; fewer imports; simpler examples. Con: dynamic runtime registration harder (edge case, can add escape hatch later).

**Selected:** Policies in config (Alternative B). Rationale: consistent with the config-driven direction; same entry-point resolution as make_env; PolicyRegistry becomes an internal implementation detail.

## Acceptance Criteria

- [x] `make_push_env`, `make_grid_env`, and `register_gridworld_policies` deleted from the library; scenario-specific env creation code moved to example modules.
- [x] Generic `make_env(entry_point, **params)` added to the library; accepts string ("module:callable") or callable; used by all examples.
- [x] `SimpleRecord` (and internal record envelope type) not exported from `doagent` or `doagent.validation`; record shape documented for consumers of `listen()` etc. without exposing the type.
- [x] Session (or a single runner entry point) accepts a config dict that specifies at least: shared_data (e.g. type: "memory" | "file", path?), topology (mode, visibility?), run_config (logging_level?), and policy definitions; library instantiates adapters internally.
- [x] Users can run push and gridworld flows without importing `doagent.core` or `doagent.records`; only `doagent` (and optionally `doagent.validation` for high-level run helpers) used in examples.
- [x] Push and gridworld validation examples updated to use config-driven path; env creation lives in example code or a generic local helper, not in the library.
- [x] Re-export from `doagent` any types needed for the documented "run from config" or "Session with config" usage (so no `from doagent.core import ...` in user/example code).

## Implementation Notes

- Define a config schema (e.g. shared_data.type, topology.mode, policies as list/dict with name + entry_point + params).
- Add factory layer: config -> InMemorySharedData / FileSharedData, TopologyConfig, RunConfig, PolicyRegistry (loading policies by entry_point). Session already accepts these; the new layer builds them from config.
- Delete `make_push_env` (doagent/validation/push/envs.py), `make_grid_env` (doagent/validation/gridworld/env.py factory fn), and `register_gridworld_policies` from the library. Move env creation into example modules (e.g. examples/validation/push/env.py, examples/validation/gridworld/env.py).
- Add generic `make_env` to `doagent` (or `doagent.env`); implementation: if string, split on ":", importlib.import_module, getattr, call; if callable, call directly.
- Update `doagent/__init__.py` to stop exporting `SimpleRecord` if currently exported; document "listen() returns iterable of record-like dicts" in adapter docstring.
- Tests: update to use config-driven path where appropriate; ensure no tests rely on importing make_push_env/make_grid_env from the library for the "official" API.

## Related

- CIP: 0001 (Library First Architecture), 0002 (Shared Data Model)
- Discussion: Option C (no make_env), Option B (SimpleRecord internal), config-only surface

## Progress Updates

### 2026-03-04
Task created. Aligns with decision: no scenario-specific make_env; config-driven API; SimpleRecord internal; generic solution for push and gridworld examples.

### 2026-03-09
Alternatives explored for generic make_env mechanism. Three options considered: string-only, callable-only, hybrid (string or callable). Hybrid selected (Alternative C): fits config-driven direction (YAML) and keeps programmatic usage simple. Backlog task updated with full alternatives and rationale. Generic make_env implemented; scenario-specific factories deleted; examples and tests updated. CIP-0001 updated with reflection.

### 2026-03-09 (continued)
Alternatives explored for policy registration. Two options: keep PolicyRegistry explicit (A) vs policies in config as entry points (B). Alternative B selected: consistent with config-driven direction, same entry-point mechanism as make_env.

Post-run inspection API discussed. `session.inspect("kind")` chosen as public method -- reflects transparency as a first-class concept and connects to interpretability/traceability/provenance/accountability requirements. No Session.shared_data property needed; inspect() delegates to internal adapter. Property-specific methods (e.g. session.traceability()) deferred to CIPs 0006-0009.

Next: implement session.inspect(), Session.from_config policy resolution, migrate examples to config-only imports.

### 2026-03-09 (final)
All acceptance criteria met. Implementation complete:

- **session.inspect(kind)** added to Session -- returns records by kind from the internal adapter, replacing direct shared_data.listen() for post-run inspection.
- **Session.from_config policies** -- config dict accepts a `policies` key mapping name to entry point (string or callable). Session resolves each, builds PolicyRegistry internally.
- **create_agents registry optional** -- when no registry is passed, Session uses its internal registry built from config. Users never import PolicyRegistry.
- **Session.from_config shared_data types** -- supports "memory", "file", and "noop" (for baseline runs).
- **session.topology_mode** and **session.hub_id** properties -- allow examples to check topology without importing Topology enum.
- **Push example** fully config-driven: only imports `from doagent import Session, make_env` and `from doagent.validation import RunReporter, ...`. No doagent.core or doagent.records imports.
- **Gridworld example** fully config-driven: same pattern. Uses _make_session_config helper. Removed InMemoryParticipationRegistry (energy model uses plain set).
- **topology_comparison** analysis script updated to config-driven Session.
- **test_session_integration.py** updated to config-driven: no doagent.core or doagent.records imports; uses Session.from_config with callable policies.
- **New test** test_inspect_returns_records validates session.inspect().

**Reflection:** The public API surface for user code is now: `doagent.Session`, `doagent.make_env`, and optionally `doagent.validation` for reporting. All internal wiring (adapters, topology config, policy registry) is handled by Session.from_config. The library is fully environment-agnostic and configuration-driven.
