---
id: "2026-03-28_pluggable-llm-policy"
title: "Create pluggable LLM policy with factorization and IDK support"
status: "Completed"
priority: "High"
created: "2026-03-28"
last_updated: "2026-03-28"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies:
- "2026-03-28_policy-return-shape-and-decide"
- "2026-03-28_reasoning-field-in-payload"
tags:
- backlog
- policy-factorization
- idk
- llm
---

# Task: Create pluggable LLM policy with factorization and IDK support

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Create a policy callable that wraps an LLM API call, producing the full factorized response: `choice` (with status), `reasoning` (chain-of-thought trace), and `explanation`.

**Key characteristics:**
- **Model-agnostic:** Configured via env var or config dict (API key, model name, provider). No hardcoded model or provider.
- **Factorized output:** The LLM produces reasoning (Z) and then a structured choice (A), both recorded via the new fields.
- **IDK / abstain:** When the LLM signals low confidence or inability to act, the policy returns `choice: {status: "abstain", action: null}` with reasoning explaining why.
- **Error handling:** Parse failures or API errors produce `choice: {status: "error", action: null, error: {...}}`.

**Return shape:**

```python
return {
    "choice": {"status": "act", "action": 4},
    "reasoning": {"trace": "I observe the agent is near...", "steps": [...]},
    "explanation": "Goal-seek based on proximity to landmark.",
}
```

## Acceptance Criteria

- [x] LLM policy callable accepts a `request` dict and returns the new response shape.
- [x] Model/provider is configurable (not hardcoded).
- [x] API key handled via environment variable (user provides their own LLM callable — zero library dependency).
- [x] Policy correctly produces `status: "act"`, `status: "abstain"`, and `status: "error"` outcomes.
- [x] Reasoning trace is populated from LLM chain-of-thought (and from automatic tool tracing).
- [x] Unit tests with mocked LLM responses cover act, abstain, and error cases.

## Implementation Notes

- The prompt structure presents the observation, goal, and action space, asking for JSON with `action`, `confidence`, and `reasoning`.
- Zero LLM dependencies: the user provides any callable via per-agent `tools` config. The library wraps it for tracing.
- **Scope expanded during Stage 3:** In addition to the LLM policy example, we built a library-level **tool-tracing mechanism** inside `SessionAgent.decide()`. Per-agent tools registered in the agent config are wrapped by `_TraceCollector`, which captures I/O as reasoning steps. The hybrid `merge_reasoning()` combines tool traces with policy-provided reasoning.
- The LLM policy is a user-space callable in `examples/llm_policy.py`. The tool-tracing infrastructure is library core (`doagent/core/_internal/trace_collector.py`).

## Related

- CIP: [0002](../../cip/cip0002_shared-data-model.md)
- Parent task: [2026-03-27_talk-policy-factorization-idk-library](./2026-03-27_talk-policy-factorization-idk-library.md)
- Depends on: [2026-03-28_policy-return-shape-and-decide](./2026-03-28_policy-return-shape-and-decide.md), [2026-03-28_reasoning-field-in-payload](./2026-03-28_reasoning-field-in-payload.md)

## Progress Updates

### 2026-03-28

Task created as sub-task 5 of 6. Design decision: model-agnostic, pluggable via config/env var.

### 2026-03-28 (completed)

Implemented with expanded scope from Stage 3 deliberation:

**Library core (new capability):**
- `_TraceCollector` internal class: wraps callables, captures I/O as structured steps with timing
- `merge_reasoning()`: hybrid merge of tool traces + policy-provided reasoning
- `SessionAgent.__init__` accepts optional `tools: Dict[str, Callable]` from agent config
- `SessionAgent.decide()` wraps tools, injects into `request["tools"]`, collects traces after policy call
- `session.create_agents()` passes per-agent `tools` from config
- Reasoning gated at Level 2 (already built in Task 2)

**Example (user-space):**
- `examples/llm_policy.py`: generic LLM policy, zero framework dependencies
- User provides any LLM callable via `tools: {"llm": client.chat.completions.create}`
- Prompt builds from observation + action space, parses structured JSON
- Confidence threshold maps to abstain; parse/API failures map to error

**Tests:** 19 new tests in `test_tool_tracing.py` covering `_TraceCollector`, `merge_reasoning`, session integration (Level 1 vs 2), LLM policy mock (act/abstain/error). Full suite: 114 passed, 3 skipped.
