---
author: "Christian Cabrera"
created: "2026-10-07"
id: "0015"
last_updated: "2026-10-30"
status: "In Progress"
compressed: false
related_requirements:
- "0015"
related_cips:
- "0014"
- "0002"
- "0006"
- "0007"
tags:
- cip
- evaluation
- information-theory
- observability
- recording-policy
- information-flow
title: "Recording Policies as Information Channels"
---

# CIP-0015: Recording Policies as Information Channels

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Plan approved, ready to start work
- [x] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented
- [ ] Deferred - Postponed

## Summary

This CIP evaluates a recording policy as an information channel from a multi-agent execution to the artifacts retained after the run.
It measures which questions those artifacts can answer, how much uncertainty remains, and how much storage and computation the analysis requires.
The study compares two implementations of the same multi-agent system.
One implementation coordinates agents through a DOAgent session.
The other implementation is built on the MARBLE framework used by MultiAgentBench, where each service keeps its own log.
Both implementations share the same environment rules and agent policies.
Each implementation records only what its own architecture records during a run.
The study asks which implementation allows an analyst to recover declared information-theoretic quantities more completely, more accurately, and at lower analysis cost.
It does not claim that DOAgent changes the execution's information flow.

The environment programme uses Hidden Profile as the primary environment.
A group guessing game provides the link to Lawrence's inaccessible game.
A Lewis signalling game calibrates the metrics with exact answers.
Werewolf provides external validation.
Scripted agents come first so that both implementations produce identical trajectories.
LLM agents follow after the metrics and estimators pass their gates.

The analyst may access one service log, a subset, the complete union, or a structured service trace of the MARBLE implementation.
The DOAgent implementation is evaluated at its declared logging levels.
The experiment permits a tie or a service advantage.

This CIP implements REQ-0015.
CIP-0014 and its finished Werewolf pair remain a pilot and historical record.

## Motivation

The first Werewolf comparison measured the breadth of fact propagation with normalized log support.
That quantity is a normalized Hartley entropy, but it describes game behaviour rather than the information retained by an artifact.
The complete union of nine service logs recovered the delivery curve as well as the DOAgent session.
The result shows that isolated logs can collectively retain a powerful account of the execution.

The revised evaluation must separate three claims.

1. One representation may retain more information about declared questions.
2. Two representations may retain the same information while requiring different reconstruction effort.
3. One representation may incur different capture, storage, token, or runtime costs.

These claims require different measures.
They must not be collapsed into a binary score designed to favour DOAgent.

## Research Questions

### RQ1: Information retention

How much uncertainty about declared execution questions remains after an analyst observes each retained representation?

### RQ2: Analysis cost

When two representations determine the same answer, how much data access, joining, parsing, inference, and computation does each require?

### RQ3: Recording cost

What storage, token, latency, and runtime overhead does each recording policy add?

### RQ4: Robustness to access and loss

How does answerability change when an analyst can access only part of the service logs or when records are missing?

### RQ5: Information dynamics

Can a controlled multi-agent process support credible estimates of belief entropy, mutual information, conditional mutual information, transfer entropy, and total correlation?

### RQ6: External validity

Do findings from the controlled process remain visible in an LLM-based multi-agent scenario such as Werewolf?

## Alternatives Considered

### Alternative A: Continue the existing Werewolf campaign

This option would keep normalized holder support and vote modularity as the primary measures.
It is inexpensive because the runners already exist.
It cannot provide a known probability model, stable trajectories, or enough observations for credible Shannon or transfer-entropy estimates.
It also leaves the rise residual vulnerable to the objection that the complete service logs reconstruct the audience.

This alternative is not selected.

### Alternative B: Replace Werewolf with a controlled environment

This option would provide clean variables, known distributions, and cheap repetitions.
It would support estimator validation.
It would not show that the findings transfer to natural-language agents in a realistic multi-agent scenario.

This alternative is not sufficient by itself.

### Alternative C: Controlled environment followed by realistic validation

This option first establishes the probability model and validates the estimators.
It then applies the validated measurement protocol to LLM agents and Werewolf.
The controlled and realistic studies answer different questions and are reported separately.

This alternative was selected on 2026-10-07.
Its staging from controlled to realistic environments remains in force.

### Alternative D: Shadow recorders over one neutral execution

This option feeds one neutral event stream to recorders written for the experiment.
It holds the trajectory fixed by construction.
Its recorders are imitations of a service log and of a DOAgent session rather than the systems themselves.
The result would therefore describe recorders designed by the study, not the two architectures.

This alternative was the recording design until 2026-10-15.
It is superseded by Alternative E.

### Alternative E: Two real implementations of the same system

This option implements each environment twice.
One implementation runs agents through a DOAgent session.
The other runs agents through MARBLE environments, agents, and its engine.
Both share the environment rules and agent policies, which live outside either implementation.
Scripted agents with fixed seeds produce identical trajectories in both implementations.
This check confirms that the two implementations run the same system.

This alternative is selected.
It compares the real architectures while keeping the controlled-to-realistic staging of Alternative C.

## Claim Boundary

The primary treatment is the implementation architecture.
The environment rules, agent policies, query contract, and scored seeds are held fixed across implementations.
The primary result concerns information recoverable from each implementation's artifacts and the effort required to recover it.
It does not claim that coordinating through DOAgent changes agent behaviour or information flow.

With scripted agents, both implementations must produce the same trajectory for the same seed.
Any divergence is a defect and blocks scoring.
With LLM agents, trajectories diverge between implementations.
Each implementation is then scored against the private truth of its own run.
The comparison concerns recovery fidelity and cost, not equality of the recovered metric values.

Repetitions provide samples for estimating Shannon quantities and distributions of recording and analysis costs.
They do not create turn-by-turn counterfactual pairs between independently generated LLM games.

## Comparison Criteria

The criteria are fixed before any scored run.

1. Recovery fidelity is the difference between a metric recovered from artifacts and the same metric computed from private truth.
2. Coverage is the set of declared metrics that each artifact condition can compute at all.
3. Analysis cost counts files opened, bytes read, joins, protocol-specific parsing rules, and runtime.
4. Runtime overhead measures storage, records, tokens, and wall time added by each implementation.

No single scalar ranking is required.
A tie on fidelity with a difference in cost is a valid result.

## Learning and Implementation Workflow

The implementation also serves as a guided introduction to the information theory required by this CIP.
Concepts are introduced only when the next task needs them.
The work begins with discrete examples whose answers can be calculated by hand and verified exactly in tests.

Each learning and implementation slice follows this order:

1. Explain the concept with a small concrete experiment.
2. Calculate one example manually.
3. State the mathematical definition and its assumptions.
4. Give an exact textbook or paper reference.
5. Encode the example as a small executable test.
6. Implement the corresponding experiment component.
7. Compare the code result with the manual calculation.
8. Record the concept learned and the next reading point in the studying workspace.

The initial reading path is:

- Bishop, *Pattern Recognition and Machine Learning*, Section 1.2 for discrete random variables, joint probability, marginal probability, conditional probability, and Bayes' rule
- MacKay, *Information Theory, Inference, and Learning Algorithms*, Section 2.4 for entropy and related functions
- MacKay, Section 2.6 for relative entropy and mutual information
- Cover and Thomas, *Elements of Information Theory*, Chapter 2, Sections 2.1 through 2.5 for entropy, conditional entropy, mutual information, and chain rules
- Cover and Thomas, Section 2.8 for the data-processing inequality
- Cover and Thomas, Chapter 4 for entropy rates and stochastic processes at the temporal-information stage
- Schreiber, "Measuring Information Transfer," for the gated transfer-entropy extension

The study sequence begins with outcomes, sample spaces, random variables, and probability distributions.
It then introduces logarithms, bits, self-information, Shannon entropy, Hartley entropy, joint entropy, conditional entropy, and mutual information.
Bayesian updating, Markov processes, estimator bias, transfer entropy, and Fisher information follow only when their implementation tasks require them.

New public or experiment code remains readable without the private learning narrative.
Learning reflections stay in VibeSafe progress notes and the studying workspace.

## Formal Model

Let `H` denote the complete execution history generated by the environment and agents.
Let `pi` denote a recording policy.
A recording policy is one implementation together with one analyst access condition.
Let `R_pi = pi(H)` denote the artifacts retained by that policy.
Let `Q = f(H)` denote a declared question about the execution.

Examples of `Q` include the recipient set of an event, the observation available to a decision, the decision that produced an outcome, and the path by which a fact propagated.

The central Shannon quantities are:

```text
H(Q)
H(Q | R_pi)
MI(Q, R_pi) = H(Q) - H(Q | R_pi)
```

When `Q` is a deterministic function of `R_pi`, the representation is sufficient for that question and `H(Q | R_pi) = 0`.
When no probability distribution is justified, the evaluation reports the candidate set `C_q(r)` and its Hartley ambiguity:

```text
U_q(r) = log2 |C_q(r)|
```

Hartley ambiguity is not labelled as Shannon conditional entropy.
Computational effort is not labelled as information content.

The execution history is represented as a neutral event stream defined by the environment rules.
The rules do not import DOAgent, MARBLE, or any recorder.
The neutral stream is the scoring reference.
Neither implementation reads it during a run.
Each implementation retains what its own architecture records.

## Neutral Event and Evidence Contracts

### Neutral event contract

The environment defines event types, variable domains, temporal order, and private truth.
The contract includes every variable required by the predeclared query suite.
Adding a variable only to a DOAgent record is prohibited.
Beliefs, observations, actions, outcomes, and causal variables are generated by the shared rules and policies.
Both implementations receive them under the same source contract.

The first executable contract is an immutable message-delivery event.
It contains an episode identifier, event identifier, non-negative step, sender identifier, message identifier, and actual recipient set.
This contract belongs to the controlled environment and does not import a DOAgent or service-log schema.
The recipient query derives its private scoring answer from the event before any representation is decoded.

The analytic calibration cases treat recording policies as functions of this event.
The full policy may retain the recipient set.
A local service policy may retain only whether its named service received the message.
A count policy may retain only the number of recipients.
In the implementation study, the same distinctions arise from the artifacts each implementation writes.
Representation parsers and the common decoder receive only retained artifacts.
They cannot access the neutral event or the private scoring answer.

The message-delivery event is the first vertical slice rather than the complete controlled-event vocabulary.
State, observation, belief, action, transition, and outcome events remain part of this task.

### Data boundaries

The environment owns a private truth store.
It contains latent states, random draws, channel outcomes, and the values used to derive scoring answers.
No representation parser or query decoder can access this store.

The shared environment rules write the neutral event stream and private truth to a scoring sink.
Neither implementation can read the scoring sink.
Some events contain facts that also determine a scoring answer.
For example, an implementation must deliver a message before it can record the delivery.
The scorer derives and stores the answer separately rather than passing a privileged answer object to an implementation.

Each implementation turns the run into retained artifacts through its own recording mechanism.
Representation parsers receive only the artifacts allowed by their access condition.
The common decoder receives only neutral evidence produced by those parsers.
Agents receive their environment observations and messages, not the neutral event stream.

### Common event identity and order

Every event type has an episode identifier, event identifier, logical time step, and sequence index.
The sequence index gives a total order when several events occur during one logical step.
The concrete event class identifies the event type.
Event identifiers are unique within an episode.

The typed event base separates `logical_step` from `sequence_index`.
State truth, observations, and message deliveries now share these identity and order fields.

### Private state truth

A state-truth entry contains the latent state and the random choice that produced it.
It may link to the previous state-truth entry.
It is available to the environment and scorer only.
An implementation can record a derived state fact only when the environment emits an observation or outcome to an agent.

### Observation events

An observation event names the observing agent, observation symbol, channel configuration, and source truth identifier.
The source identifier provides provenance without revealing the latent value.
The named agent receives the observation symbol.

### Message-delivery events

A message-delivery event names the sender, message, actual recipient set, and relevant observation or action identifiers.
Recipient agents receive the message payload.
A service log typically retains one service-specific receipt.
A DOAgent session may retain the declared audience of the record.

### Belief events

A belief event names the reporting agent, state alphabet, probability vector, and declared input event identifiers.
The probabilities must be finite, non-negative, and sum to one.
Both implementations elicit beliefs with the same policy and prompt.
Each can retain the reported belief under its own representation.
Belief values are measurement outputs and are not inferred from hidden model state.

### Action events

An action event names the acting agent, action symbol, and declared input event identifiers.
Input identifiers record which observations, messages, or beliefs were supplied when the action was selected.
These links are recorded enablers rather than causal-effect claims.

### Transition events

A transition event names the action and other declared inputs supplied to the environment mechanism.
It links the previous and next private state-truth identifiers without exposing their latent values.
The environment mechanism and its stochastic choice remain available to the scorer.
Implementations observe only the transition effects that the environment exposes to agents.

### Outcome events

An outcome event names the public outcome symbol and the transition event that produced it.
It may include the agents allowed to observe the outcome.
The transition link supports provenance queries.
It does not establish counterfactual causation by itself.

### Representation parsers

Each representation has a parser that maps retained artifacts into a neutral evidence model.
The parser may only use artifacts available under that representation's access condition.
Parser implementation and execution cost are measured as part of analysis cost.
Parser rules are frozen before the scored campaign.

### Common query decoder

One common decoder answers the query suite from the neutral evidence model.
The decoder contains no branches for DOAgent, service logs, or structured tracing.
It returns an exact answer, an explicit unknown value, or a candidate answer set.
The neutral evidence model follows environment and query semantics rather than copying the DOAgent schema.

## Hypotheses

The hypotheses do not presume that DOAgent wins.

- H1: The union of complete service logs and a complete DOAgent session can be informationally sufficient for many event-delivery questions.
- H2: Explicit event identities and trace links reduce ambiguity for relationship questions that prose logs leave underdetermined.
- H3: A DOAgent session requires fewer cross-file joins and protocol-specific parsing rules for the same declared questions.
- H4: Individual or partial service-log views retain less global execution information than the complete service-log union.
- H5: Structured service tracing can match DOAgent on information retention when it records equivalent fields.
- H6: Recording policies form an information-cost frontier rather than a single total ordering.

## Environment Programme

### Shared structure

Every environment is split into three parts.
The rules define state, observations, messages, transitions, outcomes, and private truth through `reset` and `step`.
The policies decide what each agent sends, believes, and does.
The two implementations connect the same rules and policies to DOAgent or to MARBLE.
Rules and policies import neither DOAgent nor MARBLE.

The first agents are scripted or Bayesian policies with known updates.
They provide an oracle for estimator validation and an identical-trajectory check across implementations.
LLM policies are a later validation layer.

Each agent reports a probability vector over a declared alphabet at declared measurement points.
Belief reports are scored for calibration so low entropy is not mistaken for correct knowledge.
Both implementations elicit beliefs identically.

Episodes have a fixed horizon and fixed measurement points in the estimator-validation stage.
Independent seeds generate repeated episodes from the same declared stochastic process.
Natural-language messages are added only after the discrete estimators pass validation.

### Calibration: Lewis signalling game

One agent observes a hidden state and sends a message to some recipients.
The recipients report beliefs and act on the state.
The existing one-round walking skeleton implements this game with policies inside the environment.
It is refactored into rules and policies before it is used for calibration.

The game gives exact references by enumeration.
It calibrates `H(Q)`, `H(Q|R)`, and `MI(Q, R)` for recipient-set queries and for belief and action variables.
It is not expected to separate the two implementations, because every relationship is one hop.

### Primary: Hidden Profile

Several agents must choose one option from a small set.
Each agent holds some facts about the options.
Shared facts favour a wrong option, while the facts that favour the correct option are split across agents.
The group can choose correctly only if agents pass their unshared facts to each other.
The paradigm comes from Stasser and Titus and has an LLM benchmark in HiddenBench.

The scripted first version uses a fixed topology, a finite fact alphabet, and a declared sharing rule per round.
Beliefs over the options follow from the facts each agent holds.
Measured quantities include:

- which agents held fact `f` at round `t`, and which message first gave it to them
- the path that carried an unshared fact from its source to each agent
- `H(correct option | facts held by agent i)` at each round
- `MI(correct option, messages received by agent i)`
- belief entropy and calibration of each agent before the final vote

These questions depend on who received which message and when.
They are the questions where per-service logs and a shared session record are most likely to differ in recoverability or cost.
Hidden Profile is therefore the primary environment.

### Bridge: group guessing game

Agents repeatedly guess numbers whose sum must hit a hidden target.
After each round, they hear only whether the total was too high or too low.
The design follows Riedl's study of emergent coordination in LLM groups.

Measured quantities include:

- marginal entropy `h_i` of each agent's guess
- joint entropy `H` of all guesses in the same round
- multi-information `I = sum_i h_i - H`, also called total correlation
- relative entropy from each agent's belief to the true posterior
- time-delayed mutual information between agents' guesses across rounds

Per-agent logs give each `h_i`.
The joint entropy `H` needs the guesses of every agent aligned in the same round.
When every log carries a round index, that alignment is a simple join.
A tie in recoverability is therefore expected unless alignment is made hard by asynchrony or partial access.
The game is kept as the bridge to Lawrence's quantities rather than as the primary test.
An optional variant lets agents message each other between rounds.

### External validation: Werewolf

Werewolf already exists as a DOAgent implementation and a MARBLE service implementation.
It adds hidden roles, deception, public and private communication, and variable populations.
Only metrics and decoders validated in the earlier environments are applied to it.

### Complexity progression

1. Lewis signalling calibration with scripted agents.
2. Hidden Profile with scripted agents in both implementations.
3. Group guessing game with scripted agents in both implementations.
4. Hidden Profile and the guessing game with LLM agents.
5. Werewolf with validated measures.

Advancing a level requires the preceding level to pass its declared gate.

## Recording Conditions

Each condition is an implementation together with an analyst access condition.
The service conditions are views of the MARBLE implementation's artifacts.
The DOAgent conditions are views of the DOAgent implementation's session.
The environment rules and agent policies do not know which implementation runs them.

The MARBLE implementation uses MARBLE's environment, agent, and engine classes, as the Werewolf service runner does.
It is not an imitation written for this study.
Its native logging is kept unchanged.

### S1: Individual service log

Each agent retains only its local observations, messages, decisions, and outcomes.
The analyst receives one named log.

### Sk: Partial service-log union

The analyst receives a declared subset of the agent logs.
Subset size and selection procedure are recorded.

### Sall: Complete service-log union

The analyst receives every service log.
This condition tests whether isolated logs collectively reconstruct the global execution.

### Sstructured: Structured service tracing

A service-oriented baseline adds competent service telemetry to the MARBLE implementation.
It records timestamps, caller, callee, message identifier, payload, and declared parent identifiers.
Its schema is designed from service-tracing practice and the neutral event contract.
It does not automatically receive DOAgent record fields or shared-data links.
This baseline prevents raw prose logs from becoming a straw man.

### D0, D1, and D2: DOAgent recording policies

The DOAgent implementation runs agents through a real `Session` and is evaluated at its declared logging levels.
The exact records available at each level are listed before execution.
No decoder may use fields outside its assigned level.

## Query Suite

The questions are fixed before the scored campaign.
Each one is either a record question or a link question.
A record question is answered by reading the record in front of you.
A link question starts at one record and follows a link to earlier records.
If the link is missing, the answer is not stated.
The three dimensions together make a decision interpretable.

### Accountability

Record questions:

- Who sent this message?
- Who received this message?
- Who could see this fact by this round?
- Who acted, and what did they choose?

Link question:

- Which votes produced the group choice?

### Traceability and provenance

Record questions:

- In what order did these events happen?
- Which message first delivered this fact to this player?

Link questions:

- What was the player looking at when they decided?
- Which earlier records does this decision point at?
- What path did this fact take from its source to this player?
- Which update produced this result?

### Explainability

Record question:

- What chances did this player report?

Link questions:

- Why did this player vote this way?
- How did the chances change after this message?
- Did this vote pick the route the chances ranked first?

How much the final vote says about the hidden deal is a summary across games.
It is not a question about one game.

## Metrics

### Exact answerability

A fixed decoder produces an answer or an explicit unknown value.
Exact-match accuracy, coverage, precision, and recall are reported where appropriate.
Decoder development uses separate pilot seeds.
Scored seeds remain held out.

### Residual ambiguity

The evaluator enumerates candidate answers when the representation does not identify one answer.
The score is `log2` of the candidate count.
Protocol constraints define the valid answer space before artifacts are inspected.

### Shannon quantities

The controlled process supports estimates of:

- entropy of hidden states and reported beliefs
- conditional entropy after observations or retained records
- conditional entropy of an action given the inputs its decision record declares
- mutual information between hidden states and beliefs, messages, actions, or decoded answers
- conditional mutual information along declared communication links
- relative entropy from a reported belief to the posterior implied by the facts that agent held
- total correlation across agent states, defined as multi-information below
- time-delayed mutual information between agents across rounds

Multi-information over agent variables `A_1, ..., A_n` is:

```text
I = h_1 + ... + h_n - H(A_1, ..., A_n)
```

Each `h_i` is the entropy of one agent's variable.
`H` is the joint entropy of all agents' variables at the same step.
The marginal entropies need only one agent's records.
The joint entropy needs records of all agents aligned at the same step.

Relative entropy is:

```text
D(P || Q) = sum over x of P(x) log2(P(x) / Q(x))
```

`P` is the distribution treated as true.
A cell where `P` is positive and `Q` is zero contributes positive infinity.
Mutual information is the relative entropy of the joint against the product of its marginals, which gives a consistency check between the two functions.

The conditional entropy of an action given its declared inputs reads a DOAgent decision record directly.
The agent update stores the inputs in the same record as the action.
A service log stores the message text, so the same joint is available only after the decoder recovers the input set.
Under scripted policies the true value is zero, because the action is a function of the held facts.
A positive value from a reconstructed input set is then reconstruction error, in bits.
With LLM agents a positive value against the true inputs means the action depended on something the record omitted.

Raw high-dimensional text is not passed directly to a mutual-information estimator.
Text conditions use a fixed decoder to produce declared discrete variables or probability vectors.

### Trace and causal terminology

A DOAgent trace establishes that an update was recorded as an enabler of a state transition.
It does not by itself prove that changing that update would change the outcome.
Primary queries therefore use the terms recorded input, dependency, or enabler.
Causal effect and responsibility are reserved for an explicit causal model or intervention study.

### Transfer entropy

Transfer entropy is estimated only when the controlled process supplies enough repeated transitions over stable variables.
The intended form is:

```text
T_(M -> B) = CMI(B_(t+1), M_t | B_t)
```

The analysis reports estimator assumptions, history length, alphabet size, and finite-sample correction.
Transfer entropy is omitted when the kill test shows that the estimate is unstable.
Its omission does not prevent completion of the core CIP.

### Belief quality

Belief entropy is reported with calibration and proper scoring rules.
Relative entropy from the reported belief to the posterior implied by the held facts gives that calibration in bits.
Brier score or log loss distinguishes justified confidence from confident error.

### Analysis cost

The evaluation records files opened, bytes read, records scanned, joins, protocol-specific rules, and runtime.
Implementation size may be descriptive but is not treated as a fundamental information measure.

### Recording cost

The evaluation records stored bytes, record count, duplicated content, tokens, model calls, and wall time.
Cost boundaries are identical across compared conditions.

### Information-cost frontier

Each recording policy is plotted by retained information and capture cost.
No single scalar ranking is required.
The frontier shows whether additional recording cost buys additional answerability or lower uncertainty.

### Considered and declined

Partial information decomposition was considered for the group question.
Hidden Profile is synergistic in structure, because no agent alone identifies the correct option and the pooled facts do.
The decomposition was declined.
Several incompatible definitions of redundancy exist, and defending one of them is outside this study.
Multi-information already supplies the group-level quantity.

## Statistical Plan

The controlled environment supplies exact reference quantities where analytic calculation is possible.
Simulation verifies each estimator against those references before any LLM run.

Sample size is selected by estimator simulation rather than an arbitrary repetition count.
The number of joint states must remain small relative to the sample count.
Bias-corrected or Bayesian estimators are compared with the plug-in estimate.
Bootstrap confidence intervals are reported across independent episodes.
Held-out decoding prevents extraction rules from being fitted to scored trajectories.

The analysis reports all attempted primary metrics.
Metrics are not removed because they tie or favour a service condition.

## Information Topography Bridge

Categorical belief distributions form an exponential family.
Their natural parameters and Fisher information metric provide a candidate state space for studying information topography.
The controlled environment can therefore measure belief trajectories, local Fisher geometry, entropy change, and multi-information under known communication constraints.

The inaccessible game is stated in terms of marginal entropies `h_i`, joint entropy `H`, and multi-information `I = sum_i h_i - H`.
Under its information-isolation axiom, the sum of marginal entropies stays constant.
The group guessing game supplies the same three quantities over agent guesses.
This makes it the closest empirical counterpart in the programme.
The connection to the recording comparison is limited.
Marginal entropies are recoverable from per-agent records, while joint entropy and multi-information need aligned records of all agents.
That difference matters only when alignment across records is not trivial.

This bridge is gated on a formal mapping between the experiment's random variables and the inaccessible game's state variables.
The inaccessible game assumes information isolation, while DOAgent deliberately records an observable execution.
The evaluation therefore studies an instrumented or accessible counterpart.
It does not claim that a DOAgent session directly implements the inaccessible game.

The bridge is omitted from empirical claims if the mapping cannot be stated without metaphor.
Its omission does not prevent completion of the core CIP.

## Optional Causal Extension

Environment-specific causal variables belong in the neutral event contract and environment payloads.
The generic record envelope remains independent of environment semantics.
A causal model may declare variable domains, parent relationships, transition mechanisms, intervention semantics, and exogenous-noise distributions.
Run metadata stores the model identifier and version.
Individual events store variable values and references needed for replay.

Recording these variables enables causal analysis but does not identify causality by itself.
Identification must come from a declared transition mechanism, justified observational assumptions, or controlled interventions.

An intervention runner may snapshot the state before a transition, hold other actions and environment randomness fixed, replace one action, and compare outcomes.
Stochastic effects require repeated matched interventions.
Joint effects may require combination tests or an explicit attribution rule.
This extension begins only after the core controlled campaign passes Gate 4.

## Werewolf External Validation

The finished `werewolf_kimi_5` repetition 01 remains a pilot.
It demonstrates that complete service logs can recover the normalized holder-support curve.
It also demonstrates that the session stores event audiences as typed data.

No new Werewolf campaign starts before the controlled kill test.
The binary rise residual is not a primary metric.
Later Werewolf runs reuse only metrics and decoders that passed the controlled validation.

Werewolf may expose role probabilities before each vote if belief elicitation is added.
That intervention must be reported because it can change agent behaviour.
Natural-language results do not replace the discrete estimator-validation results.

## Kill Test and Decision Gates

### Gate 1: Formal identifiability

Every primary quantity must name its random variables, probability distribution, and observation conditions.
Failure to do so stops implementation and returns the CIP to design.

### Gate 2: Estimator recovery

Simulation estimates must recover known analytic quantities within a declared tolerance and confidence interval.
Failure removes the unstable metric or changes the environment before LLM experiments.

### Gate 3: Implementation fairness

Both implementations must share the same environment rules, agent policies, and seeds.
Scripted agents must produce identical trajectories in both implementations.
The MARBLE implementation must use MARBLE's own classes and native logging.
The structured service baseline must have field availability justified independently of DOAgent.
Failure blocks comparative claims.

### Gate 4: Measurable distinction

The pilot must reveal either an information-retention difference, an analysis-cost difference, or a justified tie.
A tie is a valid result.
An architecture claim without a measurable distinction is not advanced to an expensive campaign.

### Gate 5: External validation

Only validated metrics proceed to LLM agents and Werewolf.
The publication target is selected after this gate.

## Core Acceptance Boundary

The core CIP is complete through Gate 4 when:

- the formal model and neutral contracts are fixed
- the analytic reference model is validated
- the calibration game and Hidden Profile are implemented on DOAgent and on MARBLE with scripted agents
- scripted runs produce identical trajectories in both implementations
- representation parsers and the common decoder are frozen
- primary Shannon and Hartley measures pass estimator validation
- the controlled scored campaign reports information retention, ambiguity, analysis cost, and recording cost
- the result states whether DOAgent wins, ties, or loses for each query and cost dimension

The group guessing game, LLM agents, causal interventions, Werewolf, transfer entropy, Fisher geometry, and the information-topography bridge are gated extensions.
Their backlog tasks may exist, but they cannot start until their dependency gates succeed.
Failure or omission of an extension does not prevent the core CIP from reaching Implemented status.

## Design Constraints

These constraints came out of reviewing the two-implementation plan before the backlog tasks were created.
They exist to stop the comparison from being decided by how the study was set up rather than by the frameworks.

### The contribution is observability, not capability

The two implementations run the same rules and the same policies, so they must reach the same outcome.
The claim is about what can be recovered from the artifacts afterwards, never about which framework plays better.
Any statement that DOAgent improves task performance is out of scope for this CIP.

### Trajectory parity is defined on the neutral event sequence

Parity is checked by comparing the neutral event stream each implementation produced for a given seed against the stream the rules emit with no framework attached.
The streams must match in order, identity, and content.
Artifacts are expected to differ, and that difference is the measurement.
Comparing artifacts for parity would be comparing the thing under study.

### The structured service condition is optional

`Sstructured` is a service system that logs to a declared schema.
It is a deliberately strong baseline and may match DOAgent on many queries.
It is implemented only if time allows, and it is not required for Gate 4.

### A tie against the strongest baseline is a result

If `Sall` or `Sstructured` ties with DOAgent, that is reported as a tie.
The informative part is then the cost dimension: what each implementation had to record, and what the analysis cost, to reach the same answers.
A tie is not treated as a failed experiment and does not trigger a search for a query suite that breaks it.

### The query suite is frozen before any scored run

Queries are fixed at Gate 1 and are not revised after artifacts have been inspected.
Adding a query once the artifacts are known would be choosing the question to fit the answer.

### The reference configuration is frozen before scoring

The Hidden Profile fact set, allocation rule, topology, horizon, and scoring rule are fixed before the first scored comparison.
Changes after that point invalidate the reference quantities and the campaign has to restart.

### The MARBLE implementation must be idiomatic

The baseline is reviewed by someone who knows MARBLE, and the review is an acceptance criterion rather than a test.
A baseline built to lose produces a result about this study, not about service architectures.

### The scoring sink is unreachable from both implementations

Neither run may open the private-truth file.
A query that cannot be answered from the artifacts is recorded as unanswerable, which is a measurement, not a defect to work around.

## Implementation Plan

1. **Formal specification**
   - Define the execution history, recording policy, representations, query family, and answer spaces.
   - Define which quantities are Shannon, Hartley, computational, or economic.
   - Define primary hypotheses and stopping rules.

2. **Analytic reference model**
   - Specify the categorical hidden-state process and Bayesian agents.
   - Calculate reference entropies, mutual information, and belief updates where possible.
   - Simulate sample-size and estimator bias before choosing repetition counts.

3. **Calibration environment**
   - Split the signalling walking skeleton into rules with `reset` and `step` and separate scripted policies.
   - Write private truth independently from every analysed artifact.
   - Verify deterministic replay from seeds.

4. **Two implementations**
   - Implement Hidden Profile rules and scripted policies.
   - Run them through a DOAgent session and through MARBLE environments, agents, and engine.
   - Verify identical trajectories for identical seeds.
   - Document the fields and access available to every condition.
   - Prevent truth leakage into artifact decoders.

5. **Query decoders**
   - Implement one parser per representation into the neutral evidence model.
   - Implement one common decoder against the same query contract.
   - Return explicit unknown and candidate sets rather than inventing missing facts.
   - Freeze parsers and the decoder before the scored campaign.

6. **Estimator validation**
   - Compare empirical estimates with analytic references.
   - Test bias correction, confidence intervals, and held-out behaviour.
   - Apply the kill test to unstable metrics.

7. **Controlled scored campaign**
   - Run the selected number of independent episodes.
   - Report information retention, ambiguity, analysis cost, and recording cost.
   - Construct the information-cost frontier.

8. **Guessing game and LLM validation**
   - Implement the group guessing game in both implementations and measure multi-information.
   - Replace controlled policies with model-backed policies while retaining the same measurement contract.
   - Fix an LLM call budget from estimator sample-size results.
   - Report belief calibration and behavioural changes caused by elicitation.
   - Repeat only metrics that passed estimator validation.

9. **Werewolf validation**
   - Decide whether and how to add structured beliefs to Werewolf.
   - Run a predeclared campaign only after the controlled results justify it.
   - Compare conclusions with the preserved pair 1 pilot.

10. **Theory and publication decision**
    - Evaluate the formal bridge to Fisher geometry and information topography.
    - State limitations of observation, intervention, and finite samples.
    - Select the venue from the demonstrated contribution rather than a predetermined tier.

## Backward Compatibility

This CIP does not change the public DOAgent API during the design and kill-test stages.
Experimental environments and both implementations remain under `experiments/`.
The MARBLE implementation depends on the MARBLE checkout used by the Werewolf service runner.
Any later public API proposal requires a separate requirement or an explicit extension of this CIP before implementation.

CIP-0014 remains available as the history of the MultiAgentBench Werewolf pilot.
CIP-0012 remains the separate failure-attribution study.

## Testing Strategy

Unit tests use small distributions with analytically known entropy and mutual information.
Property tests verify probability normalization, deterministic seeded generation, topology constraints, and truth isolation.
Trajectory parity tests confirm that scripted runs produce the same neutral event stream in both implementations.
Decoder tests cover exact answers, unknown answers, candidate sets, missing artifacts, and prohibited truth access.
Estimator tests compare simulated estimates with analytic references.
Integration tests run one complete episode through both implementations and every access condition.

Live LLM tests begin only after the controlled suite passes.

## Related Requirements

- [REQ-0015: Quantifiable Information-Theoretic Observability](../requirements/req0015_information-theoretic-observability.md)

This CIP provides the controlled process, recording conditions, estimators, cost measures, and realistic validation required by REQ-0015.

## Backlog Tasks

### Core tasks

- [Formal information-channel specification](../backlog/features/2026-10-07_formal-information-channel-specification.md)
- [Analytic information-flow reference model](../backlog/features/2026-10-07_analytic-reference-model.md)
- [Signalling calibration environment](../backlog/features/2026-10-07_controlled-information-flow-environment.md)
- [Hidden Profile environment rules and scripted policies](../backlog/features/2026-10-15_hidden-profile-environment.md)
- [Hidden Profile on DOAgent](../backlog/features/2026-10-15_hidden-profile-doagent-implementation.md)
- [Hidden Profile on MARBLE](../backlog/features/2026-10-15_hidden-profile-marble-implementation.md)
- [Multi-information, relative entropy, and declared-input conditional entropy](../backlog/features/2026-10-15_multi-information-metric.md)
- [Neutral evidence and common query pipeline](../backlog/features/2026-10-07_common-query-decoding-pipeline.md)
- [Information-theoretic estimator validation](../backlog/features/2026-10-07_information-estimator-validation.md)
- [Controlled observability campaign](../backlog/features/2026-10-07_controlled-observability-campaign.md)

### Gated extension tasks

- [Group guessing game on DOAgent and MARBLE](../backlog/features/2026-10-15_group-guessing-game-implementations.md)
- [Environment-declared causal interventions](../backlog/features/2026-10-07_causal-intervention-extension.md)
- [LLM information-flow validation](../backlog/features/2026-10-07_llm-information-flow-validation.md)
- [Werewolf information-flow validation](../backlog/features/2026-10-07_werewolf-information-flow-validation.md)
- [Temporal information-flow estimation](../backlog/features/2026-10-07_transfer-entropy-extension.md)
- [Information-topography bridge](../backlog/features/2026-10-07_information-topography-bridge.md)

Extension tasks remain Proposed until their dependency gates succeed.

### Superseded tasks

- [Shadow recorders and fair baselines](../backlog/features/2026-10-07_shadow-recording-baselines.md) was replaced by the two-implementation tasks on 2026-10-15.

## Implementation Status

- [x] Record the revised research direction and alternatives
- [x] Review and accept the fixed-history representation-policy design
- [x] Replace shadow recorders with two real implementations of the same system
- [x] Pass Gate 1 with a formal specification
- [ ] Define the analytic reference model
- [x] Pass Gate 2 with validated estimators
- [x] Refactor the signalling calibration into rules and policies
- [x] Implement Hidden Profile rules, the scripted policy, and the exact deal count
- [x] Implement Hidden Profile on DOAgent and on MARBLE with identical scripted trajectories
- [x] Freeze the query suite and decoders
- [x] Freeze the Hidden Profile reference configuration
- [x] Pass Gate 3 with fair baselines
- [ ] Run the controlled scored campaign
- [x] Pass Gate 4 with a measurable result or justified tie
- [ ] Optionally implement the group guessing game and measure multi-information
- [ ] Run LLM validation
- [ ] Pass Gate 5 before any new Werewolf campaign
- [ ] Optionally validate causal interventions
- [ ] Optionally validate transfer entropy
- [ ] Evaluate the information-topography bridge
- [ ] Select the publication target

## References

- C. E. Shannon, "A Mathematical Theory of Communication," 1948.
- T. M. Cover and J. A. Thomas, *Elements of Information Theory*, second edition.
- D. J. C. MacKay, *Information Theory, Inference, and Learning Algorithms*.
- T. Schreiber, "Measuring Information Transfer," 2000.
- L. Paninski, "Estimation of Entropy and Mutual Information," 2003.
- J. C. Baez, T. Fritz, and T. Leinster, "A Characterization of Entropy in Terms of Information Loss," 2011.
- N. D. Lawrence, "The Inaccessible Game," arXiv:2511.06795, 2025.
- Z. Zhu et al., "MultiAgentBench," ACL 2025.
- D. Lewis, *Convention: A Philosophical Study*, 1969.
- A. Lazaridou, A. Peysakhovich, and M. Baroni, "Multi-Agent Cooperation and the Emergence of (Natural) Language," ICLR 2017.
- R. Lowe, J. Foerster, Y.-L. Boureau, J. Pineau, and Y. Dauphin, "On the Pitfalls of Measuring Emergent Communication," AAMAS 2019.
- N. Jaques et al., "Social Influence as Intrinsic Motivation for Multi-Agent Deep Reinforcement Learning," ICML 2019.
- G. Stasser and W. Titus, "Pooling of Unshared Information in Group Decision Making," Journal of Personality and Social Psychology, 1985.
- "HiddenBench: Assessing Collective Reasoning in Multi-Agent LLMs via Hidden Profile Tasks," arXiv, 2025.
- C. Riedl, "Emergent Coordination in Multi-Agent Language Models," arXiv, 2025.
- P. L. Williams and R. D. Beer, "Nonnegative Decomposition of Multivariate Information," arXiv:1004.2515, 2010.
- J. T. Lizier, "JIDT: An Information-Theoretic Toolkit for Studying the Dynamics of Complex Systems," Frontiers in Robotics and AI, 2014.
- CIP-0014, "Information Flow on MultiAgentBench."
- CIP-0002, "Shared Data Model as Agent Interface."
- CIP-0006, "Interpretability Records."
- CIP-0007, "Trace Records and Lineage Links."

## Progress Updates

### 2026-10-07

The Werewolf pilot was insufficient for the broad information-theoretic claim because complete service logs recovered the existing propagation curve.
The evaluation was redesigned around recording policies as information channels.
No additional server campaign should begin until the controlled environment passes the formal and estimator kill tests.
The review fixed the primary claim to analysis of one shared execution.
It added neutral environment events, representation-specific parsers, one common decoder, instrumentation parity, precise trace terminology, a staged complexity ladder, and a core acceptance boundary.
Transfer entropy, causal interventions, LLM agents, Werewolf, and information topography remain gated extensions.

### 2026-10-08

Core implementation started in `experiments/information_flow`.
The first exact measures are self-information, Shannon entropy, and Hartley ambiguity.
Eleven tests reproduce the three-agent delivery calculations, the biased protocol, candidate-set ambiguity, and invalid-input behaviour.

### 2026-10-14

Exact conditional entropy and mutual information were added over discrete joint probability tables.
The full, local-A, and count policies now provide analytic calibration cases.
Independent and perfectly correlated variables provide control cases.
The exact metrics suite passes 21 tests.

Placement was checked against CIP-0013 and the three-layer architecture.
The work evaluates DOAgent and service representations, so it remains internal under `experiments/information_flow`.
It does not enter the public `doagent` package or the end-user `examples` layer.

A labelled joint-distribution builder preserves query and recording-policy values around the low-level probability matrix.
The first typed execution contracts separate private `StateTruth` from recorder-visible observations and message deliveries.
Every typed event now distinguishes logical model time from total sequence order.
Observation events retain state provenance identifiers without exposing latent state values.
An unscored one-round environment now samples a four-valued hidden state for three heterogeneous agents.
It emits observations, one message delivery, Bayesian belief reports, categorical actions, and scored outcomes.
The same seed reproduces private truth and the complete neutral event stream.
This walking skeleton does not pass a scoring gate or replace the unfinished analytic reference model.
The complete information-flow suite passes 38 tests.

### 2026-10-15

The study was realigned to compare two real implementations of the same multi-agent system.
One implementation uses a DOAgent session and the other uses MARBLE, as the Werewolf pair already does.
Shadow recorders were superseded because they would compare recorders written by the study rather than the two architectures.

A literature review of information-theoretic multi-agent experiments selected the environment programme.
Hidden Profile is primary because its information travels through messages, where the two record styles can differ.
The group guessing game is the bridge to the inaccessible game through marginal entropy, joint entropy, and multi-information.
Its recoverability is expected to tie when every log carries a round index.
The signalling walking skeleton becomes the calibration case after its policies move out of the environment.
Werewolf remains the external validation.

The review raised five constraints that are now part of the design.
Scripted agents must produce identical trajectories in both implementations.
LLM runs are scored against their own private truth because their trajectories diverge.
The service side uses MARBLE's own classes rather than an imitation.
LLM campaigns need a call budget derived from estimator validation.
Comparison criteria are fixed before any scored run.

A second review of the realigned plan produced the Design Constraints section.
The contribution is observability and never task capability.
Trajectory parity is defined on the neutral event sequence rather than on artifacts, since artifacts are the thing being compared.
The structured service condition is optional, and a tie against it is reported as a tie rather than treated as a failure.
The query suite and the Hidden Profile reference configuration are frozen before scoring.
The MARBLE baseline must pass an idiomatic-implementation review, and neither run may open the scoring sink.

The five backlog tasks the environment programme needed now exist.
Hidden Profile has one task for framework-independent rules and scripted policies, one for the DOAgent session, and one for the MARBLE services.
Multi-information, relative entropy, and declared-input conditional entropy share one metric task.
The group guessing game is Proposed behind a gate that requires a scored Hidden Profile result first.
The decoder, campaign, and LLM tasks no longer depend on the superseded shadow-recorder task.
The reference-model task now targets the Hidden Profile enumeration, with the signalling skeleton kept as a calibration case.

A review of the metric suite added two exact measures and one reconstruction check.
Relative entropy supplies belief calibration in bits and cross-checks mutual information.
Conditional entropy of an action given its declared inputs reads a DOAgent decision record directly, and under scripted policies it scores decoder fidelity.
Recovered fact paths are checked with the data processing inequality: information about the correct option cannot increase from one recorded copy of a fact to the next.
Partial information decomposition was considered and declined, because multi-information already answers the group question and the redundancy definitions disagree.

### 2026-10-21

Gate 1 passed after a plain-language review of the specification.
The review covered the recording policy as an information channel, the separation of bits from cost, the fixed question list, and hypotheses that allow a tie or a service advantage.
A transition record now stores the action, the other inputs, and the hidden-state identifiers for one environment step, without storing the hidden values.
The guessing-game task now matches the plan: agents guess numbers that must sum to a hidden target and hear whether the sum was too high or too low.
The signalling episode does not emit a transition, because its hidden colour does not change.
The signalling game is now split into rules and a scripted policy.
Hidden Profile rules and a scripted policy run one episode with no framework attached.
That episode stays unscored until the estimator gate passes.
`reference.py` counts 18 equally likely deals.
The correct route is the same in every deal, so its entropy is zero.
Who is dealt the bridge fact, and who receives it, each carry `log2(3)` bits.

### 2026-10-22

Hidden Profile rules, the scripted policy, and the 18-deal count are in place.
The reported-belief entropy is the spread of the three route probabilities, about 0.96 bits after the first round and about 1.00 bits after the later rounds.
The correct route stays certain in every deal.
Nothing is scored.
The reference configuration is not frozen.
The next build runs the same rules through a DOAgent session and through MARBLE.

### 2026-10-23

Both runners play the same scripted episode.
Seed 17 matches the no-framework episode on DOAgent and on MARBLE, including the vote.
Neither run writes the scoring sink.
The vendored MARBLE engine module does not import, because its evaluator file does not parse.
The coordinator asks every agent once per round in ring order.
MARBLE writes five component logs.
An analyst view then returns one named log, a named subset, or every log.
An optional structured service trace is written beside the prose logs, one JSON line per engine call.
The parent of each call is the engine run.
On the questions already compared, that file ties with the rules.
The tie is not a scored result.
Nothing is scored.
Seed 17 was then timed on this machine.
One untimed pass was followed by five timed passes, each in a fresh folder.
DOAgent at logging level 1 had a median of 0.008072 seconds.
MARBLE, writing all five logs, had a median of 0.003862 seconds.
Tokens and model calls were zero.
Timing the other logging levels remains open.
The eight analyst questions and the three answer kinds are now in code.
The decoder reads the rules' event list.
Seed 0 checks that list: agent C is dealt f6 and sends it to agent A in round 1.
The transition question is unknown, because this game writes no transition event.
The query suite and the decoders are frozen for any later scored run.
The eight questions are recipients, fact_access, first_access, decision_observation, decision_action, transition_update, decision_inputs, and event_order.
An answer is one value, unknown, or a candidate set.
The shared decoder is `queries.py`.
The parsers are `parse.py` for the session file and the MARBLE logs, and `service_trace.py` for the optional trace.
Nothing is scored.
A version hash of these files is not recorded yet.
The Hidden Profile reference configuration is frozen for any later scored run.
The options, in tie-break order, are route-hill, route-tunnel, and route-bridge.
The facts are f1 tunnel weight 2 shared, f2 tunnel weight 1 shared, f3 hill weight 2 private, f4 hill weight 2 private, f5 hill weight 2 private, and f6 bridge weight 1 private.
The ring is agent-a to agent-b, agent-b to agent-c, and agent-c to agent-a.
There are three disclosure rounds and then a vote.
Shared facts start in every hand.
The three hill facts are dealt one to each agent.
The bridge fact goes to an agent whose hand still does not identify the correct option alone.
Those shuffles collapse to 18 equally likely deals.
The correct option is the unique option with the greatest total weight, which is route-hill.
A vote and a tied group decision both break ties by option order.
This configuration lives in `rules.py` as the default game.
Nothing is scored.
The scripted pilot is the 18-deal table.
The session file, the full MARBLE logs, and the optional trace recover the same answers on every deal.
Reading the session file takes one file, no joins, and 77,012 bytes.
Reading the full MARBLE logs takes four files, two joins, and 1,831 bytes.
Reading the optional trace takes one file, no joins, and 4,411 bytes.
That pilot is not a scored result.
A plug-in sample from the same 18 deals was then compared with two exact quantities.
Who holds the bridge fact has entropy 1.585 bits.
Agent A's belief entropy after round 0 is 0.9635 bits.
Two deals missed the holder entropy by 1.585 bits.
Eighteen draws with replacement missed it by 0.170 bits.
Four thousand draws landed within 0.001 bits of both exact values.
At that point Gate 2 was still open.
The MARBLE fairness review accepts the environment, the agents, and the component logs.
The 18-deal tie is a cost result for message facts.
Who received the bridge fact, who could access it, and how each agent voted are written on the log line.
Those questions do not need a trace.
The transition question is unknown in the rules as well, because this game writes no transition.
In the rules, each vote points at that agent's belief, and the belief points at the observations behind it.
The session stores a trace at logging level 1.
The group guessing game remains a later bridge.
A tie is expected there when every log carries a round number.

### 2026-10-29

The session file now answers what each vote was based on.
The reader follows the link from the vote to the decision note.
That note holds the chances for each route and the fact names in hand.
On all 18 deals those answers match the rules.
A log line that only names the chosen route is read as not stated.
The same check is applied to the log lines and to the optional structured file.
A line that does state the chances and the fact names is kept.
The lines this game writes do not state them.
The service log was checked against MARBLE's own agent logger.
That logger writes the task text, the prompt, and the result.
It does not write the hand or the chances as their own fields.
The task text for this game is one fixed sentence.
The scripted agent does not store the hand in memory.
The original logger would therefore still leave the vote basis unstated.
The study logger writes only the chosen action.
It omits the fixed task sentence.
That omission does not hide a basis the original logger would have shown.
The 18-deal result stands.
Nothing is scored.
The turn order is a short loop in the experiment.
MARBLE does not ship this game.
Werewolf keeps its turn order inside its own environment.
That run does not load MARBLE's shared engine either.
The shared engine still cannot be imported, because its scorer file does not parse.
That fact is not a remaining task.
The players, the environment, and the logs are MARBLE's.
The loop only asks each player and passes the choice on.

A sample count passes when it is less than 0.05 bits from the exact answer.
Each of 2 deals, 18 deals, and 4,000 deals was drawn 1,000 times.
The same deal can come up more than once.
A sample size is kept when at least 950 of those 1,000 draws pass.
Who received the bridge fact is 1.585 bits when every deal is played.
None of the 2-deal draws passed, and 419 of the 18-deal draws passed.
Those two sizes are not kept.
All 1,000 draws of 4,000 deals passed, so that size is kept.
The middle of those counts sat between 1.584 and 1.585 bits.
How uncertain agent A is after the first round is 0.9635 bits when every deal is played.
900 of the 2-deal draws passed, which is short of 950, so that size is not kept.
All 1,000 draws of 18 deals passed, and all 1,000 draws of 4,000 deals passed.
Both of those sizes are kept for this count.
A later run that cannot play every game needs 4,000 plays to keep both counts.
Nothing is scored.
The question deck is the three dimensions above.
The group result names every vote that produced it.
A log that does not name those votes leaves that question unanswered.
Which update produced the result stays unanswered in this game.
There is no separate step between the votes and the group choice.
The session file and the full logs answer who sent the bridge fact and the path that fact took.
The session file also answers the chances behind each vote.
The logs do not.
How the chances changed after a message is answered from the rules.
The session file does not store a belief before and after each message, so that question stays unanswered there.
Every vote in this game picks the route the chances rank first.
The session reader now follows the links from each vote to the vote round's result.
On all 18 deals those votes match the rules.
A session file with no such links leaves that question unanswered.
The logs still do not name the votes.
The reader also reads the chances stored on each disclosure round's result.
It pairs them with the chances stored on the previous round.
On all 18 deals that change matches the rules.
A round that does not state those chances leaves the question unanswered.
The logs still do not state them.
Which update produced the result stays unanswered.
Nothing is scored.
The sample check now covers every exact count for this game.
The correct route does not vary, so that count is kept at 2 deals, 18 deals, and 4,000 deals.
How uncertain the route remains given one player's facts is kept at all three sizes.
How much that player's messages say about the route is kept at all three sizes.
How uncertain each player's reported chances are is kept at 18 deals and at 4,000 deals.
It is not kept at 2 deals.
Who holds the bridge fact is kept only at 4,000 deals.
Who receives it is kept only at 4,000 deals.
How much the three holdings overlap is kept only at 4,000 deals.
18 deals is not enough for those three counts.
The squared error of a reported chance list uses the same 0.05 line.
It is not a bit count.
That score stayed within the line at 2 deals, 18 deals, and 4,000 deals.
The information lost when a chance is scored is in bits.
A reported chance of zero for the route that happened is infinite.
In this game the reported chance matches the chance implied by the facts.
The distance between those two lists is zero.
A chance list that allows a route the reference rules out has an infinite distance.
That case is checked by hand, not by this game.
The plain count is kept when it is within 0.05 of the known answer.
Its interval must also contain the known answer at least 90 percent of the time.
The interval is the estimate plus or minus 1.96 times the spread of earlier repeats.
Each repeat draws whole deals.
Four counts use a corrected value instead.
They are who holds the bridge fact and who receives it.
They also include how much the three holdings overlap.
The fourth is how much agent A's hand and agent B's hand share, given the holder.
The plain version of those counts sits a little low.
At 4,000 deals the plain holder count is about 0.0004 bits low.
Its interval covers 87 percent of the repeats.
The corrected holder count is about 0.000006 bits low.
Its interval covers 95 percent of the repeats.
The correction adds a small term for each category that appeared.
It is not clipped.
Two deals still miss the holder count.
Repeating one deal leaves that count at zero.
The correction does not close that gap when only one holder appears.
18 deals is still not enough for that count.
After the first round, the holder's uncertainty given one player's facts needs 4,000 deals.
The plain count is kept there, because the interval covers.
The correct route does not vary.
Its correction is zero, so the plain count is kept.
A missing answer is not given a bit count.
A list of possible answers uses the size of the list.
That is not a chance distribution invented for the list.
No count was dropped.
A later game that cannot list every deal should use 4,000 deals.
This game still scores all 18 deals.
Checkpoint 2 passes.
Nothing is scored.
A MARBLE run can now name its view.
One named log, a named subset, all five component logs, or only the structured file.
A run that names no view still writes every log and the structured file.
Two runs of the same view match once the clock is removed from each line.
The structured file matches once its timestamp is removed.
The session file is not the same bytes on a second run.
The library gives each record a new id and a clock.
With those fields removed, the two files match.
Links are compared by each record's place in the file.
The byte-for-byte line on the session task fails.
The library is left unchanged.
Each time is the middle of five fresh runs after one warm-up, on this machine.
Level 0 took 0.027019 seconds.
Level 1 took 0.028447 seconds.
Level 2 took 0.028679 seconds.
One component log took 0.008940 seconds.
The environment log plus agent A's log took 0.009531 seconds.
All five logs took 0.017969 seconds.
The structured file alone took 0.014591 seconds.
Tokens were zero for every setting.
The structured file records the caller, the callee, the message, the payload, and the parent call.
The parent is the engine run.
It does not copy a session record.
The MARBLE review is complete.
The environment, the agents, and the component logs are the baseline.
The engine stays as it is.
Checkpoint 3 passes.
Nothing is scored.
The score covers all 18 deals.
There is no sample range.
Each deal is asked 18 questions.
That is 324 answers per view.
A view matches when its answer equals the rules.
Both matching is a tie.
Only the session matching is a win.
Only the other view matching is a loss.
Neither matching is a blank.
An answer of not stated matches when the rules say the same.
The transition question is a tie for every view.
The game records no step between the votes and the group choice.
Session level 1 matches all 324 answers.
Session level 2 matches the same 324.
Both average 77,012 bytes read and the same number stored.
Session level 0 matches 198 answers.
It averages 66,102 bytes.
It stores no trace.
The group votes are then a blank against every log view.
The three vote bases are blanks too.
So is whether each vote matches the reported chances.
Level 0 still matches the chances and the belief change.
The log views do not.
Agent C's log matches 48 answers.
It averages 460 bytes read.
The three agent logs match 108 answers.
They average 1,380 bytes.
All component logs match 162 answers.
They average 1,831 bytes read.
They average 1,995 bytes stored.
The extra 164 bytes are the engine log.
The reader does not open that log.
The structured file matches 162 answers.
It averages 4,411 bytes.
Level 1 against all component logs has 162 wins and 162 ties.
It has no losses and no blanks.
The wins are the group votes, the chances, and the belief change.
They also include the vote bases and the vote checks.
The ties are the sender, the recipients, and access to the bridge fact.
They also include that fact's path, each vote, and the transition.
No session level loses a question to a MARBLE view.
Level 0 against all component logs has 36 wins and 162 ties.
It has 126 blanks and no losses.
The plot puts average bytes read across.
The share of matching answers goes up.
Checkpoint 4 passes.
The wider campaign list stays open.
This game has no sample interval.
The extension games are not started.
Three more figures recover information quantities from the files.
Belief entropy rises from about 0.96 bits to about 1.00 bits.
All three session levels match that curve.
The MARBLE files do not state the reported chances, so they have no curve.
Who holds the bridge fact has entropy 1.585 bits.
The session file, all component logs, and the structured file match it.
Agent C's log and the three agent logs do not state the opening hands.
The same split holds for holder and recipient, and for multi-information.
Multi-information stays about 1.17 bits across the three rounds.
Those bit charts repeat the rules whenever a file states the inputs.
The question results are now split by dimension and by record or link.
Record questions are read from the line in front of you.
Link questions follow a declared link.
Session levels 1 and 2 recover the stated questions in all three dimensions.
The log files recover many record questions and miss the link questions.
They also miss the reported chances.
The question about which update produced the group choice is not in the game.
The figures for this pilot sit in output/hidden_profile.
That folder has no timestamp, and git ignores output.
The plot functions live in the Hidden Profile package.
They are three separate passes, not one study command.
The library README stays the install and demo guide.
The next task is one timestamped study run.
That task has not been started.
