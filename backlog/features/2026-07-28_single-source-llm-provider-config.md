---
id: "2026-07-28_single-source-llm-provider-config"
title: "Configure LLM provider and model in one place"
status: "Ready"
priority: "High"
created: "2026-07-28"
last_updated: "2026-07-28"
category: "features"
related_cips:
- "0011"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- llm
- configuration
- examples
---

# Task: Configure LLM provider and model in one place

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Today the model is set in YAML (`model: "gpt-4o"`) but the provider is chosen in Python: the runner calls
`create_llm_tool()`, which quietly defaults to OpenAI. Put a Gemini model name in the config and you still get an
OpenAI client, then a confusing failure.

Move `provider` into the YAML next to `model` and drive `create_llm_tool` from it, so one file decides which service
is called and with which model. Also pass a request timeout to the provider SDK, so a stuck HTTP call fails quickly
rather than relying only on the library limit.

All provider code stays in the examples. The library must not depend on any provider SDK.

## Acceptance Criteria

- [ ] `provider` is set in the YAML next to `model`.
- [ ] Setting a Gemini model in config produces a Gemini client, and the same for OpenAI.
- [ ] A request timeout is passed to the provider SDK.
- [ ] Configurations without `provider` keep working as they do now.
- [ ] Missing keys still produce a clear error in local runners.
- [ ] No provider SDK is imported by the library.

## Implementation Notes

`create_llm_tool(provider=...)` already accepts a provider argument, so this is mostly wiring config through instead
of relying on the default.

Each provider currently accepts two environment variable names (for example `OPENAI_API_KEY` and
`DOAGENT_OPENAI_API_KEY`). Either cut this down to one, or state plainly in the docstring why both exist — the Colab
secret case is the likely reason.

This task and the notebook cleanup are independent of the library work, and together they remove most of the setup
friction on their own.

## Related

- CIP: [0011](../../cip/cip0011_llm-agents.md)
- Code: `examples/llm_policy.py`, `examples/gridworld_demo/gridworld_demo.py`,
  `examples/gridworld_demo/gridworld_demo_config.yaml`, `examples/push_demo/push_demo.py`

## Progress Updates

### 2026-07-28

Task created when CIP-0011 was accepted. The split config was found during verification of the notebook and LLM
integration work; the repository history shows two commits switching between Gemini and `gpt-4o`, which is the same
friction.
