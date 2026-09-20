# Who&When baseline

Who&When-style collector: persist ordered agent utterances, not step
inputs. Each step is `{step, agent, content}`. `content` is the action
or message, not a DOAgent request/response envelope.

Used as an observe-only sidecar on a paired D run, and alone on a
Who&When-only cost run. On that cost run the agents do not use DOAgent:
the host loop hands outputs to the next policy.

Reference: Zhang et al., *Which Agent Causes Task Failures and When?*,
[arXiv:2505.00212](https://arxiv.org/abs/2505.00212).
