# TraceElephant-static baseline

TraceElephant-static collector: persist each scored step's input and
output, plus agent id. Each step is `{step, agent, input, output}`.
`input` is the task-facing assignment or query. `output` is the action
returned by the agent. Session envelopes and environment observations
are stripped.

Used as an observe-only sidecar on a paired D run, and alone on a
TraceElephant-only cost run. On that cost run the agents do not use
DOAgent: the host loop hands outputs to the next policy. This
interceptor must not import `doagent` recording internals.

This is the static arm only. It does not replay or intervene.

Reference: Chen et al., *Seeing the Whole Elephant* (TraceElephant),
[arXiv:2604.22708](https://arxiv.org/abs/2604.22708).
