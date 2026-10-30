"""Count every Hidden Profile deal and its exact reference quantities."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import permutations
import math

from experiments.information_flow.events import BeliefEvent, MessageDeliveryEvent
from experiments.information_flow.metrics import (
    conditional_entropy,
    hartley_ambiguity,
    mutual_information,
    shannon_entropy,
)
from experiments.information_flow.hidden_profile.rules import (
    DEFAULT_CONFIG,
    HiddenProfileConfig,
    HiddenProfileEpisode,
    _assign_private_facts,
    run_episode,
    unique_leader,
)


@dataclass(frozen=True)
class DealRecord:
    """Store one distinct deal and the game it produces.

    Args:
        allocation: Agent identifier to the private fact ids that agent was dealt.
        count: Shuffle outcomes that produce this deal.
        probability: Probability of the deal under uniform shuffles.
        correct_option: Option with the greatest total weight.
        group_decision: Option selected by the majority vote.
        held_fact_ids: Held fact ids per agent after each disclosure round.
        received_fact_ids: Fact ids received by each agent in each round.
        beliefs: Reported probabilities per agent after each disclosure round.
    """

    allocation: tuple[tuple[str, tuple[str, ...]], ...]
    count: int
    probability: float
    correct_option: str
    group_decision: str
    held_fact_ids: tuple[tuple[tuple[str, tuple[str, ...]], ...], ...]
    received_fact_ids: tuple[tuple[tuple[str, tuple[str, ...]], ...], ...]
    beliefs: tuple[tuple[tuple[str, tuple[float, ...]], ...], ...]


@dataclass(frozen=True)
class ReferenceValue:
    """Store one exact quantity for an agent and a round.

    Args:
        name: Quantity name.
        agent_id: Agent the quantity describes.
        round_index: Disclosure round the quantity describes.
        value: Quantity in bits.
    """

    name: str
    agent_id: str
    round_index: int
    value: float


@dataclass(frozen=True)
class CandidateSet:
    """Store the answers that occur for one question.

    Args:
        query: Name of the question.
        answers: Distinct answers with positive probability.
    """

    query: str
    answers: tuple[str, ...]

    @property
    def ambiguity(self) -> float:
        """Return the Hartley ambiguity of the answer list."""
        return hartley_ambiguity(len(self.answers))


@dataclass(frozen=True)
class ReferenceReport:
    """Store the enumerated deals and the exact quantities.

    Args:
        deals: Distinct deals, each with its shuffle probability.
        shuffle_count: Number of equally likely shuffle outcomes.
        correct_option_entropy: Entropy of the correct option.
        correct_option_entropy_given_held: Conditional entropy given held facts.
        correct_option_mutual_information: Mutual information with received facts.
        belief_entropy: Expected entropy of each reported belief.
        bridge_fact_id: Private fact that does not favour the correct option.
        bridge_holder_entropy: Entropy of who is dealt the bridge fact.
        bridge_delivery_mutual_information: Mutual information of holder and recipient.
        bridge_hold_multi_information: Multi-information of who holds the bridge fact.
        candidate_sets: Answers that occur for each enumerated question.
    """

    deals: tuple[DealRecord, ...]
    shuffle_count: int
    correct_option_entropy: float
    correct_option_entropy_given_held: tuple[ReferenceValue, ...]
    correct_option_mutual_information: tuple[ReferenceValue, ...]
    belief_entropy: tuple[ReferenceValue, ...]
    bridge_fact_id: str
    bridge_holder_entropy: float
    bridge_delivery_mutual_information: float
    bridge_hold_multi_information: tuple[tuple[int, float], ...]
    candidate_sets: tuple[CandidateSet, ...]


def reference_report(
    config: HiddenProfileConfig = DEFAULT_CONFIG,
) -> ReferenceReport:
    """Count every deal and return the exact reference quantities.

    Args:
        config: Hidden profile configuration.

    Returns:
        The deals and the quantities computed from them.

    Raises:
        ValueError: The configuration has no single bridge fact.
    """
    correct = unique_leader(config.facts, config.options)
    if correct is None:
        raise ValueError("the complete facts must name one option")
    decisive = tuple(
        fact
        for fact in config.facts
        if not fact.shared and fact.option == correct
    )
    others = tuple(
        fact
        for fact in config.facts
        if not fact.shared and fact.option != correct
    )
    if len(others) != 1:
        raise ValueError("the reference count expects one bridge fact")
    bridge = others[0]
    counts: Counter[tuple[tuple[str, tuple[str, ...]], ...]] = Counter()
    for order in permutations(config.agents):
        for decisive_order in permutations(decisive):
            for other_order in permutations(others):
                _hands, dealt = _assign_private_facts(
                    config,
                    order,
                    decisive_order,
                    other_order,
                    correct,
                )
                allocation = tuple(
                    (agent_id, dealt[agent_id]) for agent_id in config.agents
                )
                counts[allocation] += 1
    shuffle_count = sum(counts.values())
    deals = tuple(
        _play_deal(config, allocation, count, shuffle_count, index)
        for index, (allocation, count) in enumerate(sorted(counts.items()))
    )
    rounds = range(config.horizon)
    return ReferenceReport(
        deals=deals,
        shuffle_count=shuffle_count,
        correct_option_entropy=_correct_entropy(deals, config.options),
        correct_option_entropy_given_held=tuple(
            _held_conditional(deals, config, agent_id, round_index)
            for round_index in rounds
            for agent_id in config.agents
        ),
        correct_option_mutual_information=tuple(
            _received_mutual(deals, config, agent_id, round_index)
            for round_index in rounds
            for agent_id in config.agents
        ),
        belief_entropy=tuple(
            _expected_belief_entropy(deals, agent_id, round_index)
            for round_index in rounds
            for agent_id in config.agents
        ),
        bridge_fact_id=bridge.fact_id,
        bridge_holder_entropy=_bridge_holder_entropy(deals, config, bridge.fact_id),
        bridge_delivery_mutual_information=_bridge_delivery_mutual_information(
            deals,
            config,
            bridge.fact_id,
        ),
        bridge_hold_multi_information=tuple(
            (
                round_index,
                _bridge_multi_information(deals, config, bridge.fact_id, round_index),
            )
            for round_index in rounds
        ),
        candidate_sets=_candidate_sets(deals, config, bridge.fact_id),
    )


def _play_deal(
    config: HiddenProfileConfig,
    allocation: tuple[tuple[str, tuple[str, ...]], ...],
    count: int,
    shuffle_count: int,
    index: int,
) -> DealRecord:
    """Play one deal with the scripted policy."""
    episode = run_episode(index, config, dict(allocation))
    rounds = _round_indexes(episode)
    return DealRecord(
        allocation=allocation,
        count=count,
        probability=count / shuffle_count,
        correct_option=episode.correct_option,
        group_decision=episode.group_decision,
        held_fact_ids=episode.held_fact_ids,
        received_fact_ids=_received_fact_ids(episode, config.agents, rounds),
        beliefs=_beliefs(episode, config.agents, rounds),
    )


def _round_indexes(episode: HiddenProfileEpisode) -> tuple[int, ...]:
    """Return the disclosure rounds that recorded a belief."""
    return tuple(
        sorted(
            {
                event.logical_step
                for event in episode.events
                if isinstance(event, BeliefEvent)
            }
        )
    )


def _received_fact_ids(
    episode: HiddenProfileEpisode,
    agents: tuple[str, ...],
    rounds: tuple[int, ...],
) -> tuple[tuple[tuple[str, tuple[str, ...]], ...], ...]:
    """Return the fact ids each agent received in each round."""
    rows = []
    for round_index in rounds:
        row = []
        for agent_id in agents:
            messages = tuple(
                sorted(
                    event.message
                    for event in episode.events
                    if isinstance(event, MessageDeliveryEvent)
                    and event.logical_step == round_index
                    and agent_id in event.recipient_ids
                )
            )
            row.append((agent_id, messages))
        rows.append(tuple(row))
    return tuple(rows)


def _beliefs(
    episode: HiddenProfileEpisode,
    agents: tuple[str, ...],
    rounds: tuple[int, ...],
) -> tuple[tuple[tuple[str, tuple[float, ...]], ...], ...]:
    """Return the reported belief of each agent in each round."""
    rows = []
    for round_index in rounds:
        row = []
        for agent_id in agents:
            matches = [
                event
                for event in episode.events
                if isinstance(event, BeliefEvent)
                and event.logical_step == round_index
                and event.agent_id == agent_id
            ]
            if len(matches) != 1:
                raise ValueError("each agent must report one belief per round")
            row.append((agent_id, matches[0].probabilities))
        rows.append(tuple(row))
    return tuple(rows)


def _correct_entropy(
    deals: Sequence[DealRecord],
    options: tuple[str, ...],
) -> float:
    """Return the entropy of the correct option across deals."""
    counts = Counter(deal.correct_option for deal in deals for _ in range(deal.count))
    return shannon_entropy(_distribution(counts, options, sum(counts.values())))


def _held_conditional(
    deals: Sequence[DealRecord],
    config: HiddenProfileConfig,
    agent_id: str,
    round_index: int,
) -> ReferenceValue:
    """Return the entropy of the correct option given one agent's held facts."""
    signatures = _observed_signatures(
        deals,
        lambda deal: _signature(_lookup(deal.held_fact_ids[round_index], agent_id)),
    )
    joint = _correct_joint(
        deals,
        config.options,
        signatures,
        lambda deal: _signature(_lookup(deal.held_fact_ids[round_index], agent_id)),
    )
    return ReferenceValue(
        name="correct_option_entropy_given_held",
        agent_id=agent_id,
        round_index=round_index,
        value=conditional_entropy(joint),
    )


def _received_mutual(
    deals: Sequence[DealRecord],
    config: HiddenProfileConfig,
    agent_id: str,
    round_index: int,
) -> ReferenceValue:
    """Return mutual information between the correct option and received facts."""
    signatures = _observed_signatures(
        deals,
        lambda deal: _signature(_lookup(deal.received_fact_ids[round_index], agent_id)),
    )
    joint = _correct_joint(
        deals,
        config.options,
        signatures,
        lambda deal: _signature(_lookup(deal.received_fact_ids[round_index], agent_id)),
    )
    return ReferenceValue(
        name="correct_option_mutual_information",
        agent_id=agent_id,
        round_index=round_index,
        value=mutual_information(joint),
    )


def _expected_belief_entropy(
    deals: Sequence[DealRecord],
    agent_id: str,
    round_index: int,
) -> ReferenceValue:
    """Return the average entropy of one agent's reported belief."""
    total = sum(deal.count for deal in deals)
    weighted = [
        deal.count * shannon_entropy(_lookup(deal.beliefs[round_index], agent_id))
        for deal in deals
    ]
    return ReferenceValue(
        name="belief_entropy",
        agent_id=agent_id,
        round_index=round_index,
        value=math.fsum(weighted) / total,
    )


def _bridge_holder_entropy(
    deals: Sequence[DealRecord],
    config: HiddenProfileConfig,
    bridge_fact_id: str,
) -> float:
    """Return the entropy of the agent dealt the bridge fact."""
    counts = Counter(
        _holder(deal.allocation, bridge_fact_id)
        for deal in deals
        for _ in range(deal.count)
    )
    return shannon_entropy(
        _distribution(counts, config.agents, sum(counts.values()))
    )


def _bridge_delivery_mutual_information(
    deals: Sequence[DealRecord],
    config: HiddenProfileConfig,
    bridge_fact_id: str,
) -> float:
    """Return mutual information between the bridge holder and its recipient."""
    counts: Counter[tuple[str, str]] = Counter()
    for deal in deals:
        holder = _holder(deal.allocation, bridge_fact_id)
        recipient = _recipient(deal, bridge_fact_id)
        counts[(holder, recipient)] += deal.count
    matrix = _pair_matrix(counts, config.agents, config.agents, sum(counts.values()))
    return mutual_information(matrix)


def _bridge_multi_information(
    deals: Sequence[DealRecord],
    config: HiddenProfileConfig,
    bridge_fact_id: str,
    round_index: int,
) -> float:
    """Return multi-information of who holds the bridge fact."""
    total = sum(deal.count for deal in deals)
    joint_counts: Counter[tuple[str, ...]] = Counter()
    for deal in deals:
        held = deal.held_fact_ids[round_index]
        pattern = tuple(
            "yes" if bridge_fact_id in _lookup(held, agent_id) else "no"
            for agent_id in config.agents
        )
        joint_counts[pattern] += deal.count
    labels = [("yes", "no")] * len(config.agents)
    joint_labels = list(_product(labels))
    joint_probability = _distribution(joint_counts, joint_labels, total)
    joint_entropy = shannon_entropy(joint_probability)
    marginals = []
    for index, _agent_id in enumerate(config.agents):
        yes = sum(
            count
            for pattern, count in joint_counts.items()
            if pattern[index] == "yes"
        )
        marginals.append(shannon_entropy(_two_probabilities(yes, total)))
    return math.fsum(marginals) - joint_entropy


def _candidate_sets(
    deals: Sequence[DealRecord],
    config: HiddenProfileConfig,
    bridge_fact_id: str,
) -> tuple[CandidateSet, ...]:
    """Return the answers that occur for the enumerated questions."""
    holders = tuple(
        sorted(
            {
                _holder(deal.allocation, bridge_fact_id)
                for deal in deals
            }
        )
    )
    recipients = tuple(
        sorted({_recipient(deal, bridge_fact_id) for deal in deals})
    )
    decisions = tuple(sorted({deal.group_decision for deal in deals}))
    access = tuple(
        sorted(
            {
                ",".join(
                    agent_id
                    for agent_id in config.agents
                    if bridge_fact_id in _lookup(deal.held_fact_ids[0], agent_id)
                )
                for deal in deals
            }
        )
    )
    return (
        CandidateSet("who_was_dealt_the_bridge_fact", holders),
        CandidateSet("who_received_the_bridge_fact", recipients),
        CandidateSet("who_could_access_the_bridge_fact_after_round_0", access),
        CandidateSet("group_decision", decisions),
    )


def _correct_joint(
    deals: Sequence[DealRecord],
    options: tuple[str, ...],
    columns: tuple[str, ...],
    signature,
) -> list[list[float]]:
    """Return the joint of the correct option and one observed signature."""
    counts: Counter[tuple[str, str]] = Counter()
    for deal in deals:
        counts[(deal.correct_option, signature(deal))] += deal.count
    return _pair_matrix(counts, options, columns, sum(counts.values()))


def _observed_signatures(deals: Sequence[DealRecord], signature) -> tuple[str, ...]:
    """Return the distinct signatures in deal order."""
    seen = []
    for deal in deals:
        label = signature(deal)
        if label not in seen:
            seen.append(label)
    return tuple(seen)


def _signature(fact_ids: tuple[str, ...]) -> str:
    """Return one label for a set of fact ids."""
    if not fact_ids:
        return "none"
    return ",".join(fact_ids)


def _lookup(pairs, agent_id: str):
    """Return the value recorded for one agent."""
    for recorded_id, value in pairs:
        if recorded_id == agent_id:
            return value
    raise ValueError("agent_id must identify a recorded agent")


def _holder(
    allocation: tuple[tuple[str, tuple[str, ...]], ...],
    fact_id: str,
) -> str:
    """Return the agent dealt one fact."""
    holders = [
        agent_id
        for agent_id, fact_ids in allocation
        if fact_id in fact_ids
    ]
    if len(holders) != 1:
        raise ValueError("one agent must be dealt the fact")
    return holders[0]


def _recipient(deal: DealRecord, fact_id: str) -> str:
    """Return the agent who receives one fact."""
    recipients = [
        agent_id
        for round_rows in deal.received_fact_ids
        for agent_id, fact_ids in round_rows
        if fact_id in fact_ids
    ]
    if len(recipients) != 1:
        raise ValueError("one agent must receive the fact")
    return recipients[0]


def _distribution(
    counts: Mapping[object, int],
    labels: Sequence[object],
    total: int,
) -> list[float]:
    """Return label probabilities that sum to one."""
    values = [counts.get(label, 0) / total for label in labels]
    return _restore_total(values)


def _pair_matrix(
    counts: Mapping[tuple[str, str], int],
    rows: Sequence[str],
    columns: Sequence[str],
    total: int,
) -> list[list[float]]:
    """Return a joint matrix that sums to one."""
    matrix = [
        [counts.get((row, column), 0) / total for column in columns]
        for row in rows
    ]
    flat = _restore_total([value for row in matrix for value in row])
    width = len(columns)
    return [flat[start:start + width] for start in range(0, len(flat), width)]


def _two_probabilities(yes_count: int, total: int) -> list[float]:
    """Return a two-outcome distribution."""
    return _restore_total([yes_count / total, (total - yes_count) / total])


def _restore_total(values: list[float]) -> list[float]:
    """Adjust the largest entry so the values sum to one."""
    residual = 1.0 - math.fsum(values)
    if residual != 0.0:
        index = max(range(len(values)), key=values.__getitem__)
        values[index] += residual
    return values


def _product(factors: Sequence[Sequence[str]]) -> tuple[tuple[str, ...], ...]:
    """Return the cartesian product of string factors."""
    rows: list[tuple[str, ...]] = [()]
    for factor in factors:
        rows = [row + (item,) for row in rows for item in factor]
    return tuple(rows)
