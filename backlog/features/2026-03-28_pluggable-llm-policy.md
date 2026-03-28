---
id: "2026-03-28_pluggable-llm-policy"
title: "Create pluggable LLM policy with factorization and IDK support"
status: "Ready"
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

- [ ] LLM policy callable accepts a `request` dict and returns the new response shape.
- [ ] Model/provider is configurable (not hardcoded).
- [ ] API key handled via environment variable.
- [ ] Policy correctly produces `status: "act"`, `status: "abstain"`, and `status: "error"` outcomes.
- [ ] Reasoning trace is populated from LLM chain-of-thought.
- [ ] Unit tests with mocked LLM responses cover act, abstain, and error cases.

## Implementation Notes

- The prompt structure should present the observation and goal, ask for reasoning, then ask for a structured action choice.
- Consider a simple prompt template that works across providers (OpenAI-compatible chat API as baseline).
- For the demo, the policy should work with push and/or gridworld action spaces.
- The LLM policy is a user-space callable (not a library core component), placed in examples or a contrib module.

## Related

- CIP: [0002](../../cip/cip0002_shared-data-model.md)
- Parent task: [2026-03-27_talk-policy-factorization-idk-library](./2026-03-27_talk-policy-factorization-idk-library.md)
- Depends on: [2026-03-28_policy-return-shape-and-decide](./2026-03-28_policy-return-shape-and-decide.md), [2026-03-28_reasoning-field-in-payload](./2026-03-28_reasoning-field-in-payload.md)

## Progress Updates

### 2026-03-28

Task created as sub-task 5 of 6. Design decision: model-agnostic, pluggable via config/env var.
