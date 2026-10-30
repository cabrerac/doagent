---
id: "2026-10-15_hidden-profile-environment"
title: "Implement Hidden Profile rules and scripted policies"
status: "Completed"
priority: "High"
created: "2026-10-15"
last_updated: "2026-10-29"
category: "features"
related_cips:
- "0015"
owner: "Christian Cabrera"
dependencies:
- "2026-10-07_formal-information-channel-specification"
tags:
- backlog
- environment
- hidden-profile
- information-flow
---

# Task: Implement Hidden Profile Rules and Scripted Policies

## Description

Implement the Hidden Profile environment as framework-independent rules plus separate scripted policies.
The rules own the facts, the messages, the private truth, and the scoring reference.
The policies own what each agent discloses, believes, and votes.
Neither imports DOAgent nor MARBLE.

This task produces the shared substrate that the two implementation tasks wrap.
It produces no comparison result by itself.

## Motivation

The study compares two implementations of one system.
That is only possible when the system itself exists outside both implementations.
If the rules or the policies lived inside DOAgent, the MARBLE implementation would be a reimplementation rather than the same system.

Hidden Profile is the primary environment because its information travels through messages.
Who sent which fact to whom, and when, is exactly the question where per-service logs and a shared session record may differ.

## Justification

The paradigm comes from Stasser and Titus and has a current LLM benchmark in HiddenBench.
It gives a decision that is only reachable by pooling private facts, so information flow is load-bearing rather than decorative.

The first version is scripted and deterministic.
A declared sharing rule decides disclosures, so the run is exactly reproducible and exactly enumerable.
This version does not study emergent communication.
It studies whether the disclosure structure can be recovered from artifacts.

## Design

### Options and facts

The decision is a choice of one option from a small set.
The reference configuration uses three options:

```text
route-hill
route-tunnel
route-bridge
```

A fact is an immutable record with four fields.

```text
fact_id    unique identifier within the episode
option     the option the fact bears on
weight     signed integer contribution to that option
shared     whether every agent starts with the fact
```

The correct option is the argmax of summed weights over the complete fact set.
The shared-only argmax must be a different option.
That difference is what makes the profile hidden.

The reference configuration uses six facts.

```text
f1  route-tunnel  +2  shared
f2  route-tunnel  +1  shared
f3  route-hill    +2  private
f4  route-hill    +2  private
f5  route-hill    +2  private
f6  route-bridge  +1  private
```

Shared totals favour `route-tunnel` with `+3`.
Complete totals favour `route-hill` with `+6`.
The configuration validator must assert both conditions at construction time.

### Agents and allocation

The reference configuration uses three agents.

```text
agent-a
agent-b
agent-c
```

Every agent starts holding all shared facts.
Private facts are dealt to agents by a seeded permutation.
No agent may hold enough facts to identify the correct option alone.
The validator must assert this for every allocation the seed can produce.

### Rounds and disclosure

Episodes have a fixed horizon, three rounds in the reference configuration.
In each round, every agent discloses at most one held fact to a declared recipient set.

The scripted sharing rule is:

1. Order each agent's private facts by `fact_id`.
2. In round `r`, the agent discloses the `r`-th fact in that order, if one remains.
3. Recipients come from the configured topology for that agent.

The reference topology is a ring.

```text
agent-a -> agent-b
agent-b -> agent-c
agent-c -> agent-a
```

A ring is deliberate.
Under a full mesh, every fact reaches everyone in one round and the path queries become trivial.
Under a ring, a fact needs several hops, so the recorded path has structure to recover.

Disclosed facts are added to the recipient's held set and may be disclosed onward in later rounds.
The rules must therefore distinguish facts an agent was dealt from facts it received.

### Beliefs

An agent's belief is a distribution over options derived only from its held facts.

```text
score(option) = sum of weights of held facts bearing on that option
P(option) = exp(score) / sum over options of exp(score)
```

The softmax is a declared scoring rule, not a claim about optimal inference.
It must be documented as such.
It is deterministic, so the belief is an exact function of the held set, which keeps the reference quantities enumerable.

Beliefs are reported at a fixed measurement point in every round, after disclosures are delivered.

### Votes and outcome

After the final round, every agent votes for its argmax option, breaking ties by option order.
The group decision is the majority vote, breaking ties by option order.
The outcome is correct when the group decision equals the correct option.

### Interfaces

The rules expose the interface the DOAgent session already wraps.

```python
class HiddenProfileRules:
    agents: list[str]

    def reset(self, *, seed: int | None = None) -> dict[str, dict]:
        """Deal facts and return one observation per agent."""

    def step(self, actions: dict[str, dict]) -> dict:
        """Deliver disclosures and return observations, rewards, terminations."""
```

An observation contains only what that agent may see.

```text
round
held_facts        facts the agent currently holds
received          disclosures delivered to the agent this round
options           the option alphabet
```

An action is a disclosure or a vote.

```text
{"kind": "disclose", "fact_id": "f3", "recipients": ["agent-b"]}
{"kind": "vote", "option": "route-hill"}
```

The policies are plain callables with no framework dependency.

```python
def scripted_policy(agent_id: str) -> Callable[[dict], dict]:
    """Return a policy that discloses by the declared rule and votes by argmax."""
```

The policy signature must accept the DOAgent decision request shape, which carries the observation under `inputs`.
The MARBLE adapter passes the same mapping.

### Private truth and the scoring sink

The rules write a scoring sink that neither implementation can read.
It contains:

```text
fact allocation per agent
the correct option
held sets per agent per round
every disclosure with sender, fact, recipients, round, and sequence index
every reported belief
every vote and the group decision
```

The sink is also emitted as the neutral event stream, reusing the typed events in
`experiments/information_flow/events.py`.
A fact disclosure is a `MessageDeliveryEvent` whose message names the fact.

## Execution Plan

1. Add `experiments/information_flow/hidden_profile/__init__.py`.
2. Add `rules.py` with the `Fact`, option, topology, and configuration data classes.
3. Validate the configuration: shared argmax differs from complete argmax, and no single agent can identify the correct option.
4. Implement seeded dealing of private facts.
5. Implement `reset` returning per-agent observations.
6. Implement `step`: apply disclosures, deliver to recipients, update held sets, collect beliefs, then votes on the final round.
7. Emit neutral events for dealing, disclosure, belief, vote, and outcome, with `logical_step` as the round and `sequence_index` as the total order.
8. Write the scoring sink separately from the observations.
9. Add `policies.py` with the scripted disclosure rule and argmax vote.
10. Add `reference.py` that enumerates every allocation the seed space can produce and computes exact reference quantities.
11. Add `tests/test_hidden_profile_rules.py` covering the items in the acceptance criteria.
12. Run one episode end to end with no framework attached and record the event stream in the progress update.

## Reference Quantities

The enumeration in `reference.py` must produce, for the reference configuration:

- `H(correct option)` under the declared prior over allocations
- `H(correct option | facts held by agent i)` at the end of each round
- `MI(correct option, disclosures received by agent i)` per round
- belief entropy per agent per round
- the exact candidate set for each query in the suite

These are the values the later estimator-validation task checks against.

## Acceptance Criteria

- [x] The rules import neither DOAgent nor MARBLE.
- [x] The policies import neither DOAgent nor MARBLE.
- [x] Shared facts favour a wrong option and the complete fact set favours the correct option.
- [x] No single agent's held facts identify the correct option at round zero.
- [x] Identical seeds reproduce the allocation, the event stream, and the scoring sink.
- [x] Observations contain only facts the receiving agent holds.
- [x] The scoring sink is not reachable from any observation.
- [x] A fact received in one round can be disclosed onward in a later round.
- [x] Belief probabilities are finite, non-negative, and sum to one.
- [x] The event stream has a strict total order by `sequence_index`.
- [x] `reference.py` reproduces at least one entropy and one mutual information by enumeration.
- [x] One episode runs with no framework attached.
- [x] The reference configuration is the default game in `rules.py`.

## Implementation Notes

Keep everything under `experiments/information_flow/hidden_profile/`.
Reuse the typed events rather than defining a parallel vocabulary.

Do not let the softmax temperature become a tuning knob.
Fix it at one and document it as a declared scoring rule.

Do not add natural-language messages.
Structured disclosures keep the scripted stage free of semantic decoding.

The ring topology is a design decision, not a detail.
If it is changed to a mesh, record in the progress update that path queries become one hop.

## Dependencies and Gate

Gate 1 must be complete, since the query suite determines which fields the events must carry.
This task is a prerequisite for both implementation tasks.
It is unscored until estimator validation confirms the reference quantities.

## Related

- CIP: 0015
- Requirement: REQ-0015

## Progress Updates

### 2026-10-15

Task created after the study was realigned to compare two real implementations.
Hidden Profile is the primary environment because its information travels through messages.

### 2026-10-21

Rules, the scripted policy, and tests now live under `experiments/information_flow/hidden_profile/`.
A seeded deal keeps the hill route hidden at round zero, and a scripted episode votes `route-hill`.
The scoring record stays off the observations.
`reference.py` counts all 36 shuffles as 18 equally likely deals and plays each one.
The correct route does not vary, so its entropy and its mutual information with received facts are zero.
Who is dealt the bridge fact has `log2(3)` bits of entropy, and that fact's recipient carries the same mutual information.
The episode stays unscored until the estimator gate passes.
The reference configuration is not yet frozen for a scored comparison.

### 2026-10-22

The rules, the scripted policy, and the deal count are the current code.
The open criterion is the freeze before any scored comparison.
The next build is the DOAgent session and the MARBLE services, using these rules unchanged.

### 2026-10-29

The default game in `rules.py` is the reference configuration.
The study plan lists its options, facts, ring, and rounds.
No version stamp was stored.
