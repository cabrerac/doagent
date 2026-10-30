"""Compare sample counts with the exact Hidden Profile answers.

A draw picks deals from the full list and puts each one back.
Repeating that draw shows which sample size stays close to the exact answer.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
import math
import random

from experiments.information_flow.hidden_profile.reference import (
    DealRecord,
    ReferenceReport,
    ReferenceValue,
    _distribution,
    _holder,
    _lookup,
    _pair_matrix,
    _product,
    _recipient,
    _signature,
    _two_probabilities,
    reference_report,
)
from experiments.information_flow.hidden_profile.rules import (
    DEFAULT_CONFIG,
    HiddenProfileConfig,
)
from experiments.information_flow.metrics import (
    brier_score,
    conditional_entropy,
    conditional_mutual_information,
    corrected_conditional_mutual_information,
    corrected_mutual_information,
    corrected_shannon_entropy,
    entropy_correction,
    log_loss,
    mutual_information,
    relative_entropy,
    shannon_entropy,
)

SAMPLE_SIZES = (2, 18, 4000)
PASS_LINE_BITS = 0.05
RULE_REPEATS = 1000
RULE_KEEP = 0.95
COVERAGE_FLOOR = 0.90
INTERVAL_WIDTH = 1.96


@dataclass(frozen=True)
class SampleEstimate:
    """One plug-in estimate and its distance from the exact value.

    Args:
        name: Quantity being estimated.
        agent_id: Agent for a per-agent quantity.
        round_index: Round for a per-round quantity.
        sample_size: Number of deals in the sample.
        estimate: Plug-in value in bits.
        exact: Exact value.
            The unit is bits, except for the Brier score.
        absolute_error: Absolute difference between the estimate and the exact value.
        unit: Unit of the count.
            This is bits, or brier for the squared error of a chance list.
    """

    name: str
    agent_id: str | None
    round_index: int | None
    sample_size: int
    estimate: float
    exact: float
    absolute_error: float
    unit: str


@dataclass(frozen=True)
class RepeatedDraw:
    """How close one count stays when a draw is repeated.

    Args:
        name: Which count this row describes.
        agent_id: Player for a per-player count.
            None when the count is not about one player.
        round_index: Round for a per-round count.
            None when the count is not about one round.
        sample_size: How many deals were drawn each time.
        repeats: How many times that draw was repeated.
        passes: How many repeats were less than the pass line from the exact answer.
        kept: Whether enough repeats passed to keep this number of deals.
        exact: Exact answer.
            The unit is bits, except for the Brier score.
        low: Low end of the middle 95 percent of the counts.
        high: High end of the middle 95 percent of the counts.
        mean_error: Average of the estimate minus the exact answer.
        spread: Standard deviation of the estimates across repeats.
        coverage: Share of later repeats whose interval contains the exact answer.
            The interval uses the spread of the earlier repeats.
            It is the estimate plus or minus 1.96 times that spread.
            Each repeat draws whole deals.
        unit: Unit of the count.
            This is bits, or brier for the squared error of a chance list.
    """

    name: str
    agent_id: str | None
    round_index: int | None
    sample_size: int
    repeats: int
    passes: int
    kept: bool
    exact: float
    low: float
    high: float
    mean_error: float
    spread: float
    coverage: float
    unit: str


def sample_check(
    sample_sizes: Sequence[int] = SAMPLE_SIZES,
    seed: int = 0,
    config: HiddenProfileConfig = DEFAULT_CONFIG,
) -> tuple[SampleEstimate, ...]:
    """Draw deals from the exact list and compare plug-in estimates with it.

    Each listed deal is equally likely.
    A sample is drawn with replacement.

    Args:
        sample_sizes: Sizes of the samples to draw.
        seed: Seed for the sample draws.
        config: Hidden profile configuration.

    Returns:
        One estimate per quantity and sample size.

    Raises:
        ValueError: A sample size is not a positive integer.
    """
    sizes = _sample_sizes(sample_sizes)
    report = reference_report(config)
    prepared = _prepare(report, config)
    generator = random.Random(seed)
    estimates = []
    for size in sizes:
        drawn = tuple(generator.choices(report.deals, k=size))
        estimates.extend(_estimates(drawn, prepared, size))
    return tuple(estimates)


def repeated_deal_check(
    copies: int = 8,
    config: HiddenProfileConfig = DEFAULT_CONFIG,
) -> tuple[SampleEstimate, ...]:
    """Repeat one deal and report the resulting error.

    Args:
        copies: How many times that deal is repeated.
        config: Hidden profile configuration.

    Returns:
        Plug-in estimates for the repeated deal.

    Raises:
        ValueError: The copy count is not a positive integer.
    """
    if isinstance(copies, bool) or not isinstance(copies, int) or copies < 1:
        raise ValueError("copies must be a positive integer")
    report = reference_report(config)
    prepared = _prepare(report, config)
    drawn = (report.deals[0],) * copies
    return _estimates(drawn, prepared, copies)


def repeated_draw_check(
    sample_sizes: Sequence[int] = SAMPLE_SIZES,
    repeats: int = RULE_REPEATS,
    pass_line: float = PASS_LINE_BITS,
    keep_rate: float = RULE_KEEP,
    seed: int = 0,
    config: HiddenProfileConfig = DEFAULT_CONFIG,
) -> tuple[RepeatedDraw, ...]:
    """Repeat each draw and keep a sample size that usually stays close.

    Each listed deal is equally likely.
    The same deal can appear more than once.
    A repeat passes when its count is less than the pass line from the exact answer.
    A sample size is kept when the share of passing repeats is at least the keep rate.

    Args:
        sample_sizes: How many deals to draw each time.
        repeats: How many times to repeat each draw.
        pass_line: How far from the exact answer still counts as close, in bits.
        keep_rate: Share of repeats that must pass.
        seed: Seed for the draws.
        config: Hidden profile configuration.

    Returns:
        One row per count and sample size.

    Raises:
        ValueError: A size, the repeat count, the pass line, or the keep rate is not usable.
    """
    sizes = _sample_sizes(sample_sizes)
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1:
        raise ValueError("repeats must be a positive integer")
    if isinstance(pass_line, bool) or not isinstance(pass_line, (int, float)):
        raise ValueError("pass line must be a positive number of bits")
    if not math.isfinite(pass_line) or pass_line <= 0:
        raise ValueError("pass line must be a positive number of bits")
    if isinstance(keep_rate, bool) or not isinstance(keep_rate, (int, float)):
        raise ValueError("keep rate must be greater than zero and at most one")
    if not math.isfinite(keep_rate) or keep_rate <= 0 or keep_rate > 1:
        raise ValueError("keep rate must be greater than zero and at most one")
    report = reference_report(config)
    prepared = _prepare(report, config)
    generator = random.Random(seed)
    rows: list[RepeatedDraw] = []
    for size in sizes:
        buckets: list[list[float]] = [[] for _spec in prepared.specs]
        for _repeat in range(repeats):
            drawn = generator.choices(report.deals, k=size)
            for bucket, value in zip(buckets, _plug_in_values(drawn, prepared), strict=True):
                bucket.append(value)
        for spec, values in zip(prepared.specs, buckets, strict=True):
            passes = sum(abs(value - spec.exact) < pass_line for value in values)
            low, high = _middle_band(values)
            mean_error = math.fsum(value - spec.exact for value in values) / repeats
            rows.append(
                RepeatedDraw(
                    name=spec.name,
                    agent_id=spec.agent_id,
                    round_index=spec.round_index,
                    sample_size=size,
                    repeats=repeats,
                    passes=passes,
                    kept=passes / repeats >= keep_rate,
                    exact=spec.exact,
                    low=low,
                    high=high,
                    mean_error=mean_error,
                    spread=_spread(values),
                    coverage=_coverage(values, spec.exact),
                    unit=_unit(spec.name),
                )
            )
    return tuple(rows)


@dataclass(frozen=True)
class EstimatorDecision:
    """Which count is kept, and whether the recovery check passes.

    Args:
        primary: Which count is kept.
            This is plug-in when every kept count is the plain one.
            It names a correction when some counts use the corrected value.
        sample_size: How many deals a later game should play.
            None when no sample size met the rule.
        passed: Whether every remaining count met the rule at that sample size.
        dropped: Counts removed because neither version stayed inside the rule.
        corrected: Counts that keep the corrected value rather than the plain one.
    """

    primary: str
    sample_size: int | None
    passed: bool
    dropped: tuple[str, ...]
    corrected: tuple[str, ...]


def estimator_decision(rows: Sequence[RepeatedDraw]) -> EstimatorDecision:
    """Keep the plain count when its interval covers, and the correction when it does not.

    A count is inside the rule when the pass line and the interval both hold.
    The plain count is kept when it is inside the rule.
    The corrected count is kept only when the plain count is not.
    A count is dropped when neither version is inside the rule at 4,000 deals.
    The check passes when one sample size keeps every remaining count.

    Args:
        rows: Repeated draws for every count and sample size.

    Returns:
        The kept count, the sample size, and any dropped counts.
    """
    grouped: dict[tuple[str, str | None, int | None, int], dict[str, RepeatedDraw]] = {}
    for row in rows:
        key = (_base_name(row.name), row.agent_id, row.round_index, row.sample_size)
        grouped.setdefault(key, {})
        grouped[key]["corrected" if row.name.endswith("_corrected") else "plain"] = row
    quantities = {
        (base, agent_id, round_index)
        for base, agent_id, round_index, _size in grouped
    }
    dropped: list[str] = []
    for base, agent_id, round_index in sorted(quantities, key=_quantity_sort):
        versions = grouped.get((base, agent_id, round_index, SAMPLE_SIZES[-1]), {})
        if _chosen_version(versions) is None:
            dropped.append(_quantity_label(base, agent_id, round_index))
    dropped_labels = tuple(dropped)
    selected: int | None = None
    corrected_names: tuple[str, ...] = ()
    for size in SAMPLE_SIZES:
        chosen: list[str] = []
        covered = True
        for base, agent_id, round_index in quantities:
            if _quantity_label(base, agent_id, round_index) in dropped_labels:
                continue
            versions = grouped.get((base, agent_id, round_index, size), {})
            version = _chosen_version(versions)
            if version is None:
                covered = False
                break
            chosen.append(version)
        if covered and chosen:
            selected = size
            corrected_names = tuple(sorted(_corrected_bases(grouped, size, dropped_labels)))
            break
    if corrected_names:
        primary = "plug-in with a correction"
    else:
        primary = "plug-in"
    return EstimatorDecision(
        primary=primary,
        sample_size=selected,
        passed=selected is not None,
        dropped=dropped_labels,
        corrected=corrected_names,
    )


def _sample_sizes(sample_sizes: Sequence[int]) -> tuple[int, ...]:
    """Return the sample sizes when every size is a positive integer."""
    sizes = tuple(sample_sizes)
    if any(isinstance(size, bool) or not isinstance(size, int) or size < 1 for size in sizes):
        raise ValueError("sample sizes must be positive integers")
    return sizes


@dataclass(frozen=True)
class _Spec:
    """One exact count and where it sits in the prepared tables.

    Args:
        name: Quantity name.
        agent_id: Player for a per-player count.
        round_index: Round for a per-round count.
        exact: Exact answer in bits.
        kind: How a draw is turned into this count.
        slot: Index into the prepared table for this kind.
    """

    name: str
    agent_id: str | None
    round_index: int | None
    exact: float
    kind: str
    slot: int


@dataclass(frozen=True)
class _Prepared:
    """Per-deal labels used to count a draw.

    Args:
        specs: Counts in result order.
        options: Route names.
        agents: Player names.
        holder: Who holds the bridge fact, one label per deal.
        correct: Correct route, one label per deal.
        belief_bits: Entropy of one reported belief, one list of deals per slot.
        held: Fact names one player holds, one list of deals per slot.
        received: Fact names one player received, one list of deals per slot.
        delivery: Who holds the bridge fact and who receives it, one pair per deal.
        pattern: Who holds the bridge fact after a round, one list of deals per slot.
        brier: Squared error of one reported chance list, one list of deals per slot.
        loss: Information lost by one reported chance list, one list of deals per slot.
        divergence: Distance from a reported chance list to itself, one list of deals per slot.
        conditional: Two hands and the bridge holder, one list of deals per slot.
        decision: Group choice, one label per deal.
        deal_ids: Identity of each deal, in table order.
    """

    specs: tuple[_Spec, ...]
    options: tuple[str, ...]
    agents: tuple[str, ...]
    holder: tuple[str, ...]
    correct: tuple[str, ...]
    belief_bits: tuple[tuple[float, ...], ...]
    held: tuple[tuple[str, ...], ...]
    received: tuple[tuple[str, ...], ...]
    delivery: tuple[tuple[str, str], ...]
    pattern: tuple[tuple[tuple[str, ...], ...], ...]
    brier: tuple[tuple[float, ...], ...]
    loss: tuple[tuple[float, ...], ...]
    divergence: tuple[tuple[float, ...], ...]
    conditional: tuple[tuple[tuple[str, str, str], ...], ...]
    decision: tuple[str, ...]
    deal_ids: tuple[int, ...]


def _prepare(report: ReferenceReport, config: HiddenProfileConfig) -> _Prepared:
    """Store one label per deal for every exact count."""
    deals = report.deals
    agents = config.agents
    options = config.options
    holder = tuple(_holder(deal.allocation, report.bridge_fact_id) for deal in deals)
    correct = tuple(deal.correct_option for deal in deals)
    delivery = tuple(
        (holder_id, _recipient(deal, report.bridge_fact_id))
        for holder_id, deal in zip(holder, deals, strict=True)
    )
    belief_bits: list[tuple[float, ...]] = []
    brier_rows: list[tuple[float, ...]] = []
    loss_rows: list[tuple[float, ...]] = []
    divergence_rows: list[tuple[float, ...]] = []
    held_labels: list[tuple[str, ...]] = []
    received_labels: list[tuple[str, ...]] = []
    patterns: list[tuple[tuple[str, ...], ...]] = []
    conditional_rows: list[tuple[tuple[str, str, str], ...]] = []
    specs: list[_Spec] = [
        _Spec("bridge_holder_entropy", None, None, report.bridge_holder_entropy, "holder", 0),
    ]
    for value in report.belief_entropy:
        specs.append(_spec_from_value(value, "belief", len(belief_bits)))
        bits: list[float] = []
        brier: list[float] = []
        loss: list[float] = []
        divergence: list[float] = []
        for deal in deals:
            probabilities = _belief(deal, value.agent_id, value.round_index)
            outcome = options.index(deal.correct_option)
            bits.append(shannon_entropy(probabilities))
            brier.append(brier_score(probabilities, outcome))
            loss.append(log_loss(probabilities, outcome))
            divergence.append(relative_entropy(probabilities, probabilities))
        belief_bits.append(tuple(bits))
        brier_rows.append(tuple(brier))
        loss_rows.append(tuple(loss))
        divergence_rows.append(tuple(divergence))
    specs.append(
        _Spec(
            "correct_option_entropy",
            None,
            None,
            report.correct_option_entropy,
            "correct",
            0,
        )
    )
    for value in report.correct_option_entropy_given_held:
        specs.append(_spec_from_value(value, "held", len(held_labels)))
        held_labels.append(
            tuple(
                _signature(_lookup(deal.held_fact_ids[value.round_index], value.agent_id))
                for deal in deals
            )
        )
    for value in report.correct_option_mutual_information:
        specs.append(_spec_from_value(value, "received", len(received_labels)))
        received_labels.append(
            tuple(
                _signature(_lookup(deal.received_fact_ids[value.round_index], value.agent_id))
                for deal in deals
            )
        )
    specs.append(
        _Spec(
            "bridge_delivery_mutual_information",
            None,
            None,
            report.bridge_delivery_mutual_information,
            "delivery",
            0,
        )
    )
    for round_index, exact in report.bridge_hold_multi_information:
        specs.append(
            _Spec(
                "bridge_hold_multi_information",
                None,
                round_index,
                exact,
                "pattern",
                len(patterns),
            )
        )
        rows = []
        for deal in deals:
            facts = deal.held_fact_ids[round_index]
            rows.append(
                tuple(
                    "yes"
                    if report.bridge_fact_id in _lookup(facts, agent_id)
                    else "no"
                    for agent_id in agents
                )
            )
        patterns.append(tuple(rows))
    population = tuple(range(len(deals)))
    for slot, value in enumerate(report.belief_entropy):
        specs.append(
            _Spec(
                "belief_brier",
                value.agent_id,
                value.round_index,
                _mean(brier_rows[slot]),
                "brier",
                slot,
            )
        )
    for slot, value in enumerate(report.belief_entropy):
        specs.append(
            _Spec(
                "belief_log_loss",
                value.agent_id,
                value.round_index,
                _mean(loss_rows[slot]),
                "loss",
                slot,
            )
        )
    for slot, value in enumerate(report.belief_entropy):
        specs.append(
            _Spec(
                "belief_relative_entropy",
                value.agent_id,
                value.round_index,
                _mean(divergence_rows[slot]),
                "divergence",
                slot,
            )
        )
    for slot, value in enumerate(report.correct_option_entropy_given_held):
        specs.append(
            _Spec(
                "bridge_holder_entropy_given_held",
                value.agent_id,
                value.round_index,
                conditional_entropy(
                    _two_label_joint(population, holder, held_labels[slot], agents)
                ),
                "holder_given",
                slot,
            )
        )
    for round_index in range(len(deals[0].held_fact_ids)):
        triples = tuple(
            (
                _signature(_lookup(deal.held_fact_ids[round_index], agents[0])),
                _signature(_lookup(deal.held_fact_ids[round_index], agents[1])),
                holder_id,
            )
            for holder_id, deal in zip(holder, deals, strict=True)
        )
        conditional_rows.append(triples)
        specs.append(
            _Spec(
                "held_signature_conditional_information",
                None,
                round_index,
                conditional_mutual_information(triples),
                "conditional",
                len(conditional_rows) - 1,
            )
        )
    decision = tuple(deal.group_decision for deal in deals)
    specs.append(
        _Spec(
            "decision_mutual_information",
            None,
            None,
            mutual_information(
                _two_label_joint(population, correct, decision, options)
            ),
            "decision",
            0,
        )
    )
    specs.append(
        _Spec(
            "bridge_holder_entropy_corrected",
            None,
            None,
            report.bridge_holder_entropy,
            "holder_corrected",
            0,
        )
    )
    specs.append(
        _Spec(
            "correct_option_entropy_corrected",
            None,
            None,
            report.correct_option_entropy,
            "correct_corrected",
            0,
        )
    )
    specs.append(
        _Spec(
            "bridge_delivery_mutual_information_corrected",
            None,
            None,
            report.bridge_delivery_mutual_information,
            "delivery_corrected",
            0,
        )
    )
    for slot, (round_index, exact) in enumerate(report.bridge_hold_multi_information):
        specs.append(
            _Spec(
                "bridge_hold_multi_information_corrected",
                None,
                round_index,
                exact,
                "pattern_corrected",
                slot,
            )
        )
    for round_index, triples in enumerate(conditional_rows):
        specs.append(
            _Spec(
                "held_signature_conditional_information_corrected",
                None,
                round_index,
                conditional_mutual_information(triples),
                "conditional_corrected",
                round_index,
            )
        )
    return _Prepared(
        specs=tuple(specs),
        options=options,
        agents=agents,
        holder=holder,
        correct=correct,
        belief_bits=tuple(belief_bits),
        held=tuple(held_labels),
        received=tuple(received_labels),
        delivery=delivery,
        pattern=tuple(patterns),
        brier=tuple(brier_rows),
        loss=tuple(loss_rows),
        divergence=tuple(divergence_rows),
        conditional=tuple(conditional_rows),
        decision=decision,
        deal_ids=tuple(id(deal) for deal in deals),
    )


def _spec_from_value(value: ReferenceValue, kind: str, slot: int) -> _Spec:
    """Return a count row for one player and round."""
    return _Spec(value.name, value.agent_id, value.round_index, value.value, kind, slot)


def _plug_in_values(drawn: Sequence[DealRecord], prepared: _Prepared) -> tuple[float, ...]:
    """Return one count for each prepared row, in row order."""
    indexes = _indexes(drawn, prepared)
    total = len(indexes)
    return tuple(_plug_in(spec, indexes, total, prepared) for spec in prepared.specs)


def _indexes(drawn: Sequence[DealRecord], prepared: _Prepared) -> tuple[int, ...]:
    """Return the prepared-table index of each drawn deal."""
    by_id = {deal_id: index for index, deal_id in enumerate(prepared.deal_ids)}
    return tuple(by_id[id(deal)] for deal in drawn)


def _plug_in(
    spec: _Spec,
    indexes: tuple[int, ...],
    total: int,
    prepared: _Prepared,
) -> float:
    """Return one count from the deals in a draw."""
    if spec.kind == "holder":
        counts = Counter(prepared.holder[index] for index in indexes)
        return shannon_entropy(_distribution(counts, prepared.agents, total))
    if spec.kind == "correct":
        counts = Counter(prepared.correct[index] for index in indexes)
        return shannon_entropy(_distribution(counts, prepared.options, total))
    if spec.kind == "belief":
        bits = prepared.belief_bits[spec.slot]
        return math.fsum(bits[index] for index in indexes) / total
    if spec.kind == "held":
        joint = _option_joint(indexes, prepared.held[spec.slot], prepared)
        return conditional_entropy(joint)
    if spec.kind == "received":
        joint = _option_joint(indexes, prepared.received[spec.slot], prepared)
        return mutual_information(joint)
    if spec.kind == "delivery":
        counts = Counter(prepared.delivery[index] for index in indexes)
        matrix = _pair_matrix(counts, prepared.agents, prepared.agents, total)
        return mutual_information(matrix)
    if spec.kind == "pattern":
        return _multi_information(indexes, prepared.pattern[spec.slot], prepared, total)
    if spec.kind == "brier":
        return _mean_at(prepared.brier[spec.slot], indexes)
    if spec.kind == "loss":
        return _mean_at(prepared.loss[spec.slot], indexes)
    if spec.kind == "divergence":
        return _mean_at(prepared.divergence[spec.slot], indexes)
    if spec.kind == "holder_given":
        return conditional_entropy(
            _two_label_joint(indexes, prepared.holder, prepared.held[spec.slot], prepared.agents)
        )
    if spec.kind == "conditional":
        triples = tuple(prepared.conditional[spec.slot][index] for index in indexes)
        return conditional_mutual_information(triples)
    if spec.kind == "decision":
        return mutual_information(
            _two_label_joint(indexes, prepared.correct, prepared.decision, prepared.options)
        )
    if spec.kind == "holder_corrected":
        counts = Counter(prepared.holder[index] for index in indexes)
        probabilities = _distribution(counts, prepared.agents, total)
        return corrected_shannon_entropy(probabilities, total, _observed_support(probabilities))
    if spec.kind == "correct_corrected":
        counts = Counter(prepared.correct[index] for index in indexes)
        probabilities = _distribution(counts, prepared.options, total)
        return corrected_shannon_entropy(probabilities, total, _observed_support(probabilities))
    if spec.kind == "delivery_corrected":
        counts = Counter(prepared.delivery[index] for index in indexes)
        matrix = _pair_matrix(counts, prepared.agents, prepared.agents, total)
        return corrected_mutual_information(matrix, total)
    if spec.kind == "pattern_corrected":
        return _corrected_multi_information(
            indexes,
            prepared.pattern[spec.slot],
            prepared,
            total,
        )
    if spec.kind == "conditional_corrected":
        triples = tuple(prepared.conditional[spec.slot][index] for index in indexes)
        return corrected_conditional_mutual_information(triples, total)
    raise ValueError("kind must name a prepared count")


def _option_joint(
    indexes: tuple[int, ...],
    signatures: tuple[str, ...],
    prepared: _Prepared,
) -> list[list[float]]:
    """Return the joint of the correct route and one set of fact names."""
    counts: Counter[tuple[str, str]] = Counter()
    columns: list[str] = []
    seen: set[str] = set()
    for index in indexes:
        signature = signatures[index]
        counts[(prepared.correct[index], signature)] += 1
        if signature not in seen:
            seen.add(signature)
            columns.append(signature)
    return _pair_matrix(counts, prepared.options, columns, len(indexes))


def _observed_support(probabilities: Sequence[float]) -> int:
    """Return how many chances in a list are positive."""
    support = sum(probability > 0.0 for probability in probabilities)
    if support < 1:
        return 1
    return support


def _corrected_multi_information(
    indexes: tuple[int, ...],
    patterns: tuple[tuple[str, ...], ...],
    prepared: _Prepared,
    total: int,
) -> float:
    """Return the overlap count plus a support correction."""
    plugin = _multi_information(indexes, patterns, prepared, total)
    counts: Counter[tuple[str, ...]] = Counter(patterns[index] for index in indexes)
    addition = -entropy_correction(len(counts), total)
    for position, _agent_id in enumerate(prepared.agents):
        yes = sum(count for pattern, count in counts.items() if pattern[position] == "yes")
        support = 2 if 0 < yes < total else 1
        addition += entropy_correction(support, total)
    return plugin + addition


def _multi_information(
    indexes: tuple[int, ...],
    patterns: tuple[tuple[str, ...], ...],
    prepared: _Prepared,
    total: int,
) -> float:
    """Return how much the players' bridge-fact holdings overlap."""
    counts: Counter[tuple[str, ...]] = Counter(patterns[index] for index in indexes)
    labels = [("yes", "no")] * len(prepared.agents)
    joint_labels = _product(labels)
    joint_entropy = shannon_entropy(_distribution(counts, joint_labels, total))
    marginals = []
    for position, _agent_id in enumerate(prepared.agents):
        yes = sum(
            count
            for pattern, count in counts.items()
            if pattern[position] == "yes"
        )
        marginals.append(shannon_entropy(_two_probabilities(yes, total)))
    return math.fsum(marginals) - joint_entropy


def _two_label_joint(
    indexes: Sequence[int],
    left_labels: Sequence[str],
    right_labels: Sequence[str],
    left_alphabet: Sequence[str],
) -> list[list[float]]:
    """Return the joint of two label lists."""
    counts: Counter[tuple[str, str]] = Counter()
    columns: list[str] = []
    seen: set[str] = set()
    for index in indexes:
        right = right_labels[index]
        counts[(left_labels[index], right)] += 1
        if right not in seen:
            seen.add(right)
            columns.append(right)
    return _pair_matrix(counts, left_alphabet, columns, len(indexes))


def _mean(values: Sequence[float]) -> float:
    """Return the average of a list of numbers."""
    return math.fsum(values) / len(values)


def _mean_at(values: Sequence[float], indexes: Sequence[int]) -> float:
    """Return the average of the selected entries."""
    return math.fsum(values[index] for index in indexes) / len(indexes)


def _base_name(name: str) -> str:
    """Return the count name without a corrected suffix."""
    suffix = "_corrected"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return name


def _quantity_label(base: str, agent_id: str | None, round_index: int | None) -> str:
    """Return a short name for one count."""
    parts = [base]
    if agent_id is not None:
        parts.append(agent_id)
    if round_index is not None:
        parts.append(str(round_index))
    return " ".join(parts)


def _quantity_sort(item: tuple[str, str | None, int | None]) -> tuple[str, str, int]:
    """Return a stable order for count names."""
    base, agent_id, round_index = item
    if round_index is None:
        round_key = -1
    else:
        round_key = round_index
    return (base, agent_id or "", round_key)


def _inside_rule(row: RepeatedDraw) -> bool:
    """Return whether one row stays close and its interval covers."""
    return row.kept and row.coverage >= COVERAGE_FLOOR


def _chosen_version(versions: dict[str, RepeatedDraw]) -> str | None:
    """Return plain or corrected when that version is inside the rule."""
    plain = versions.get("plain")
    corrected = versions.get("corrected")
    if plain is not None and _inside_rule(plain):
        return "plain"
    if corrected is not None and _inside_rule(corrected):
        return "corrected"
    return None


def _corrected_bases(
    grouped: dict[tuple[str, str | None, int | None, int], dict[str, RepeatedDraw]],
    size: int,
    dropped_labels: tuple[str, ...],
) -> tuple[str, ...]:
    """Return the count names that keep the corrected value at one sample size."""
    names: list[str] = []
    for (base, agent_id, round_index, row_size), versions in grouped.items():
        if row_size != size:
            continue
        if _quantity_label(base, agent_id, round_index) in dropped_labels:
            continue
        if _chosen_version(versions) == "corrected" and base not in names:
            names.append(base)
    return tuple(names)


def _unit(name: str) -> str:
    """Return the unit of a named count."""
    if name == "belief_brier":
        return "brier"
    return "bits"


def _count_label(row: RepeatedDraw) -> str:
    """Return a short name for one repeated-draw row."""
    parts = [row.name]
    if row.agent_id is not None:
        parts.append(row.agent_id)
    if row.round_index is not None:
        parts.append(str(row.round_index))
    return " ".join(parts)


def _spread(values: Sequence[float]) -> float:
    """Return the standard deviation of a list of estimates."""
    count = len(values)
    if count < 2:
        return 0.0
    mean = math.fsum(values) / count
    variance = math.fsum((value - mean) ** 2 for value in values) / (count - 1)
    return math.sqrt(variance)


def _coverage(values: Sequence[float], exact: float) -> float:
    """Return how often an interval around a later estimate contains the exact answer.

    The spread is taken from the earlier half of the repeats.
    The later half is the check.
    The interval is that estimate plus or minus 1.96 times the spread.
    """
    half = len(values) // 2
    pilot = values[:half]
    check = values[half:]
    if not check:
        check = values
    spread = _spread(pilot)
    if spread == 0.0:
        hits = sum(abs(value - exact) <= 1e-12 for value in check)
        return hits / len(check)
    width = INTERVAL_WIDTH * spread
    hits = sum(abs(value - exact) <= width for value in check)
    return hits / len(check)


def _middle_band(values: Sequence[float]) -> tuple[float, float]:
    """Return the low and high ends of the middle 95 percent."""
    ordered = sorted(values)
    drop = int(len(ordered) * 0.025)
    if drop == 0:
        return ordered[0], ordered[-1]
    return ordered[drop], ordered[-1 - drop]


def _estimates(
    drawn: Sequence[DealRecord],
    prepared: _Prepared,
    sample_size: int,
) -> tuple[SampleEstimate, ...]:
    """Compare the plug-in values for one sample with the exact report."""
    values = _plug_in_values(drawn, prepared)
    return tuple(
        _row(
            spec.name,
            spec.agent_id,
            spec.round_index,
            sample_size,
            value,
            spec.exact,
            _unit(spec.name),
        )
        for spec, value in zip(prepared.specs, values, strict=True)
    )


def _belief(
    deal: DealRecord,
    agent_id: str,
    round_index: int,
) -> tuple[float, ...]:
    """Return one reported belief distribution."""
    for recorded_id, probabilities in deal.beliefs[round_index]:
        if recorded_id == agent_id:
            return probabilities
    raise ValueError("agent_id must identify a recorded agent")


def _row(
    name: str,
    agent_id: str | None,
    round_index: int | None,
    sample_size: int,
    estimate: float,
    exact: float,
    unit: str,
) -> SampleEstimate:
    """Return one estimate with its absolute error."""
    return SampleEstimate(
        name=name,
        agent_id=agent_id,
        round_index=round_index,
        sample_size=sample_size,
        estimate=estimate,
        exact=exact,
        absolute_error=abs(estimate - exact),
        unit=unit,
    )
