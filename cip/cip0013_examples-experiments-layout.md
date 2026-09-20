---
author: "Christian Cabrera"
created: "2026-09-19"
id: "0013"
last_updated: "2026-09-19"
status: "Implemented"
compressed: false
related_requirements:
- "0010"
- "0014"
related_cips:
- "0010"
- "0011"
- "0012"
tags:
- cip
- examples
- experiments
- validation
- reproducibility
title: "Examples and Experiments Repository Layout"
---

# CIP-0013: Examples and Experiments Repository Layout

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Design approved in the implementation plan
- [x] In Progress - Actively being implemented
- [x] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented
- [ ] Deferred - Postponed

## Summary

Reorganise repository-only examples and experiments into clear layers. Examples
remain small runnable demonstrations. Experiments contain comparisons, metrics,
and paper evaluations. Shared example support has named modules under
`examples/_shared/`, rather than a general-purpose utilities folder.

## Motivation

Provider clients, runnable scripts, scenario code, and experiment helpers are
currently mixed at package roots. Examples also import environment types from
experiments while experiment runners import examples, creating a circular
layering relationship. Several comparison runners duplicate scenario loops or
measure an empty function instead of the reported run.

## Detailed Description

The target dependency direction is:

1. `doagent` provides the public library.
2. `examples` demonstrates that library and owns reusable scenario sessions.
3. `experiments` invokes example sessions under controlled conditions and
   reports evaluation metrics.

Each example uses `run.py`, `session.py`, `env.py`, `policies.py`, and optional
`config.yaml`. Experiment `evaluate.py` modules execute one condition and
return task metrics, elapsed time, output size, and run identity. Runners vary
one parameter while keeping all other settings fixed.

Provider API calls move to `examples/_shared/llm_client.py`. Scenario policies
remain with their scenarios. The attribution evaluation moves to
`experiments/attribution/`, where it can use the shared client without adding
provider dependencies to the DOAgent package.

### Alternatives considered

- A generic `utils/` directory was rejected because it obscures ownership and
  tends to collect unrelated helpers.
- Provider clients in `doagent` were rejected because the core remains
  model- and provider-agnostic.
- A one-step breaking move was rejected in favour of compatibility shims and
  characterization tests.

## Implementation Plan

1. Add compatibility and behaviour tests.
2. Extract shared environment and LLM client support.
3. Standardise minimal, gridworld, and push examples.
4. Move attribution evaluation and add the GPT-4o judge.
5. Standardise experiment evaluators and comparison runners.
6. Update documentation and verify all tests and smoke commands.

## Backward Compatibility

Old module paths were removed. Use the canonical example, experiment,
and runner commands.

## Testing Strategy

- Canonical module paths expose the scenario entry points.
- Old compatibility paths are gone.
- Each evaluation condition executes once; the measured execution produces the
  reported metrics.
- Judge tests use a fake client and make no network calls.
- The full unit suite and no-key CLI smoke tests pass.

## Related Requirements

- REQ-0010: validation on multi-agent games.
- REQ-0014: reproducible attribution evaluation.

## Implementation Status

- [x] Characterization and compatibility tests
- [x] Shared environment and LLM client
- [x] Standardised runnable examples
- [x] Attribution experiment and judge
- [x] Experiment evaluators and runners
- [x] Documentation and full verification
- [x] Canonical implementations live in the new folders
- [x] Compatibility shims and unused experiment files removed
