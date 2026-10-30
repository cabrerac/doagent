"""Run Hidden Profile rules without a framework attached."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
import random

from experiments.information_flow.events import (
    ActionEvent,
    BeliefEvent,
    MessageDeliveryEvent,
    ObservationEvent,
    OutcomeEvent,
    RecorderInputEvent,
    StateTruth,
)


@dataclass(frozen=True)
class Fact:
    """Store one signed fact about one option.

    Args:
        fact_id: Identifier of the fact inside the episode.
        option: Option the weight applies to.
        weight: Signed point contribution.
        shared: Whether every agent starts holding the fact.

    Raises:
        ValueError: An identifier is empty or the weight is not an integer.
    """

    fact_id: str
    option: str
    weight: int
    shared: bool

    def __post_init__(self) -> None:
        """Validate the fact fields."""
        if not isinstance(self.fact_id, str) or not self.fact_id:
            raise ValueError("fact_id must be a non-empty string")
        if not isinstance(self.option, str) or not self.option:
            raise ValueError("option must be a non-empty string")
        if isinstance(self.weight, bool) or not isinstance(self.weight, int):
            raise ValueError("weight must be an integer")
        if not isinstance(self.shared, bool):
            raise ValueError("shared must be a boolean")


@dataclass(frozen=True)
class HiddenProfileConfig:
    """Configure options, facts, agents, and the disclosure ring.

    Args:
        options: Ordered option alphabet.
        facts: Facts used to score the options.
        agents: Agent identifiers in ring order.
        horizon: Number of disclosure rounds before the vote.

    Raises:
        ValueError: The profile is not hidden or one agent can see the answer.
    """

    options: tuple[str, ...]
    facts: tuple[Fact, ...]
    agents: tuple[str, ...]
    horizon: int = 3

    def __post_init__(self) -> None:
        """Validate the hidden profile."""
        if (
            not isinstance(self.options, tuple)
            or len(self.options) < 2
            or any(not isinstance(option, str) or not option for option in self.options)
            or len(set(self.options)) != len(self.options)
        ):
            raise ValueError("options must contain at least two unique names")
        if (
            not isinstance(self.agents, tuple)
            or len(self.agents) < 2
            or any(not isinstance(agent, str) or not agent for agent in self.agents)
            or len(set(self.agents)) != len(self.agents)
        ):
            raise ValueError("agents must contain at least two unique names")
        if isinstance(self.horizon, bool) or not isinstance(self.horizon, int):
            raise ValueError("horizon must be a positive integer")
        if self.horizon < 1:
            raise ValueError("horizon must be a positive integer")
        fact_ids = tuple(fact.fact_id for fact in self.facts)
        if len(set(fact_ids)) != len(fact_ids):
            raise ValueError("fact identifiers must be unique")
        if any(fact.option not in self.options for fact in self.facts):
            raise ValueError("every fact must name a configured option")
        correct = unique_leader(self.facts, self.options)
        shared = tuple(fact for fact in self.facts if fact.shared)
        shared_leader = unique_leader(shared, self.options)
        if correct is None or shared_leader is None or correct == shared_leader:
            raise ValueError("shared facts must favour a different option")
        decisive = tuple(
            fact
            for fact in self.facts
            if not fact.shared and fact.option == correct
        )
        others = tuple(
            fact
            for fact in self.facts
            if not fact.shared and fact.option != correct
        )
        if len(decisive) > len(self.agents):
            raise ValueError("too many private facts favour the correct option")
        if decisive:
            heaviest = max(decisive, key=lambda fact: fact.weight)
            worst = shared + (heaviest,) + others
            if unique_leader(worst, self.options) == correct:
                raise ValueError("one agent can identify the correct option")

    def recipients(self, agent_id: str) -> tuple[str, ...]:
        """Return the next agent in the ring.

        Args:
            agent_id: Identifier of the sending agent.

        Returns:
            The single downstream agent.

        Raises:
            ValueError: The agent is not configured.
        """
        if agent_id not in self.agents:
            raise ValueError("agent_id must identify a configured agent")
        index = self.agents.index(agent_id)
        return (self.agents[(index + 1) % len(self.agents)],)


def unique_leader(
    held: tuple[Fact, ...] | list[Fact],
    options: tuple[str, ...],
) -> str | None:
    """Return the unique highest-scoring option.

    Args:
        held: Facts included in the score.
        options: Ordered option alphabet.

    Returns:
        The leading option, or None when the top score is tied.
    """
    scores = [
        sum(fact.weight for fact in held if fact.option == option)
        for option in options
    ]
    if not scores:
        return None
    best = max(scores)
    leaders = [
        option
        for option, score in zip(options, scores)
        if score == best
    ]
    if len(leaders) != 1:
        return None
    return leaders[0]


DEFAULT_CONFIG = HiddenProfileConfig(
    options=("route-hill", "route-tunnel", "route-bridge"),
    facts=(
        Fact("f1", "route-tunnel", 2, True),
        Fact("f2", "route-tunnel", 1, True),
        Fact("f3", "route-hill", 2, False),
        Fact("f4", "route-hill", 2, False),
        Fact("f5", "route-hill", 2, False),
        Fact("f6", "route-bridge", 1, False),
    ),
    agents=("agent-a", "agent-b", "agent-c"),
    horizon=3,
)


@dataclass(frozen=True)
class HiddenProfileEpisode:
    """Hold the private scoring record and the ordered events.

    Args:
        seed: Seed that dealt the private facts.
        correct_option: Option with the greatest total weight.
        allocation: Agent identifier to the fact ids that agent was dealt.
        held_fact_ids: Held fact ids per agent after each disclosure round.
        group_decision: Option selected by the majority vote.
        events: Ordered recorder-visible events.
    """

    seed: int
    correct_option: str
    allocation: tuple[tuple[str, tuple[str, ...]], ...]
    held_fact_ids: tuple[tuple[tuple[str, tuple[str, ...]], ...], ...]
    group_decision: str
    events: tuple[RecorderInputEvent, ...]


class HiddenProfileRules:
    """Deal private facts, pass disclosures, and score the vote.

    Args:
        config: Hidden profile configuration.
    """

    def __init__(self, config: HiddenProfileConfig = DEFAULT_CONFIG) -> None:
        """Store the configuration and wait for a deal."""
        self.config = config
        self.agents = list(config.agents)
        self._phase = "new"
        self._round = 0
        self._sequence_index = 1
        self._episode_id = ""
        self._seed: int | None = None
        self._correct = ""
        self._hands: dict[str, list[Fact]] = {}
        self._dealt: dict[str, tuple[str, ...]] = {}
        self._events: list[RecorderInputEvent] = []
        self._held_history: list[tuple[tuple[str, tuple[str, ...]], ...]] = []
        self._group_decision = ""

    def reset(
        self,
        *,
        seed: int | None = None,
        allocation: Mapping[str, Sequence[str]] | None = None,
    ) -> dict[str, dict[str, object]]:
        """Deal the facts and return one observation per agent.

        Args:
            seed: Integer seed for the private-fact deal.
                Defaults to zero.
            allocation: Optional private-fact ids already assigned to each agent.
                When provided, the seed only labels the episode.

        Returns:
            One observation mapping per agent.

        Raises:
            ValueError: The seed or the allocation is invalid.
        """
        if seed is None:
            seed = 0
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        self._seed = seed
        self._phase = "disclose"
        self._round = 0
        self._sequence_index = 1
        self._episode_id = f"hidden-profile-{seed}"
        self._events = []
        self._held_history = []
        self._group_decision = ""
        self._correct = unique_leader(self.config.facts, self.config.options) or ""
        self._truth = StateTruth(
            episode_id=self._episode_id,
            event_id="state-0",
            logical_step=0,
            sequence_index=0,
            state=self._correct,
        )
        if allocation is None:
            self._hands, self._dealt = _deal(self.config, seed, self._correct)
        else:
            self._hands, self._dealt = _hands_from_allocation(
                self.config,
                allocation,
                self._correct,
            )
        for agent_id in self.config.agents:
            dealt_ids = ",".join(fact.fact_id for fact in self._hands[agent_id])
            self._append(
                ObservationEvent(
                    episode_id=self._episode_id,
                    event_id=f"deal-{agent_id}",
                    logical_step=0,
                    sequence_index=self._sequence_index,
                    agent_id=agent_id,
                    observation=dealt_ids,
                    channel_id="deal",
                    source_state_event_id=self._truth.event_id,
                )
            )
        return self._observations(received={})

    def step(
        self,
        actions: dict[str, dict[str, object]],
    ) -> dict[str, dict[str, object]]:
        """Apply one disclosure round or the final vote.

        Args:
            actions: Agent identifier to that agent's action mapping.

        Returns:
            Observations, rewards, and a finished flag for each agent.

        Raises:
            ValueError: The phase or an action is invalid.
        """
        if self._phase == "disclose":
            return self._disclose(actions)
        if self._phase == "vote":
            return self._vote(actions)
        raise ValueError("reset the rules before stepping")

    def episode(self) -> HiddenProfileEpisode:
        """Return the scoring record and the ordered events.

        Returns:
            The completed episode.

        Raises:
            ValueError: The group has not voted.
        """
        if self._phase != "done" or self._seed is None:
            raise ValueError("the episode is incomplete")
        allocation = tuple(
            (agent_id, self._dealt[agent_id])
            for agent_id in self.config.agents
        )
        return HiddenProfileEpisode(
            seed=self._seed,
            correct_option=self._correct,
            allocation=allocation,
            held_fact_ids=tuple(self._held_history),
            group_decision=self._group_decision,
            events=tuple(self._events),
        )

    def _disclose(
        self,
        actions: dict[str, dict[str, object]],
    ) -> dict[str, dict[str, object]]:
        """Deliver disclosures and record the resulting beliefs."""
        self._require_agents(actions)
        received: dict[str, list[Fact]] = {
            agent_id: [] for agent_id in self.config.agents
        }
        supplied: dict[str, list[str]] = {
            agent_id: [] for agent_id in self.config.agents
        }
        for agent_id in self.config.agents:
            action = actions[agent_id]
            if action.get("kind") != "disclose":
                raise ValueError("the disclosure step requires a disclose action")
            fact_id = action.get("fact_id")
            if fact_id is None:
                continue
            fact = self._held_fact(agent_id, fact_id)
            recipients = _recipient_set(action.get("recipients"), self.config, agent_id)
            event = MessageDeliveryEvent(
                episode_id=self._episode_id,
                event_id=f"disclosure-{self._round}-{agent_id}",
                logical_step=self._round,
                sequence_index=self._sequence_index,
                sender_id=agent_id,
                message_id=f"disclosure-{self._round}-{agent_id}",
                message=fact.fact_id,
                recipient_ids=recipients,
            )
            self._append(event)
            for recipient_id in self.config.agents:
                if recipient_id not in recipients:
                    continue
                supplied[recipient_id].append(event.event_id)
                if any(held.fact_id == fact.fact_id for held in self._hands[recipient_id]):
                    continue
                incoming = Fact(fact.fact_id, fact.option, fact.weight, False)
                self._hands[recipient_id].append(incoming)
                received[recipient_id].append(incoming)
        self._record_beliefs(self._round, supplied)
        self._held_history.append(self._held_snapshot())
        self._round += 1
        if self._round >= self.config.horizon:
            self._phase = "vote"
        rewards = {agent_id: 0.0 for agent_id in self.config.agents}
        done = {agent_id: False for agent_id in self.config.agents}
        return {
            "observations": self._observations(received),
            "rewards": rewards,
            "done": done,
        }

    def _vote(
        self,
        actions: dict[str, dict[str, object]],
    ) -> dict[str, dict[str, object]]:
        """Record the votes and the majority decision."""
        self._require_agents(actions)
        votes: dict[str, str] = {}
        vote_ids: dict[str, str] = {}
        for agent_id in self.config.agents:
            action = actions[agent_id]
            option = action.get("option")
            if action.get("kind") != "vote" or option not in self.config.options:
                raise ValueError("each vote must name a configured option")
            event_id = f"vote-{agent_id}"
            vote_ids[agent_id] = event_id
            votes[agent_id] = str(option)
            self._append(
                ActionEvent(
                    episode_id=self._episode_id,
                    event_id=event_id,
                    logical_step=self._round,
                    sequence_index=self._sequence_index,
                    agent_id=agent_id,
                    action=str(option),
                    input_event_ids=(f"belief-{self._round - 1}-{agent_id}",),
                )
            )
        self._group_decision = majority(votes.values(), self.config.options)
        correct = self._group_decision == self._correct
        self._append(
            OutcomeEvent(
                episode_id=self._episode_id,
                event_id="outcome-group",
                logical_step=self._round,
                sequence_index=self._sequence_index,
                agent_id="group",
                outcome=self._group_decision,
                action_event_id=vote_ids[self.config.agents[0]],
                contributing_event_ids=tuple(
                    vote_ids[agent_id] for agent_id in self.config.agents
                ),
            )
        )
        self._phase = "done"
        reward = 1.0 if correct else 0.0
        observations = self._observations(received={})
        for agent_id in self.config.agents:
            observations[agent_id]["phase"] = "done"
        return {
            "observations": observations,
            "rewards": {agent_id: reward for agent_id in self.config.agents},
            "done": {agent_id: True for agent_id in self.config.agents},
        }

    def _record_beliefs(
        self,
        round_index: int,
        supplied: dict[str, list[str]],
    ) -> None:
        """Record one declared belief per agent after delivery."""
        for agent_id in self.config.agents:
            probabilities = option_belief(self._hands[agent_id], self.config.options)
            inputs = tuple(supplied[agent_id]) or (f"deal-{agent_id}",)
            self._append(
                BeliefEvent(
                    episode_id=self._episode_id,
                    event_id=f"belief-{round_index}-{agent_id}",
                    logical_step=round_index,
                    sequence_index=self._sequence_index,
                    agent_id=agent_id,
                    state_labels=self.config.options,
                    probabilities=probabilities,
                    input_event_ids=inputs,
                )
            )

    def _observations(
        self,
        received: dict[str, list[Fact]],
    ) -> dict[str, dict[str, object]]:
        """Return what each agent can see."""
        phase = "vote" if self._phase == "vote" else "disclose"
        observations: dict[str, dict[str, object]] = {}
        for agent_id in self.config.agents:
            hand = self._hands[agent_id]
            dealt_ids = set(self._dealt[agent_id])
            shared_ids = {
                fact.fact_id for fact in self.config.facts if fact.shared
            }
            observations[agent_id] = {
                "phase": phase,
                "round": self._round,
                "options": self.config.options,
                "recipients": self.config.recipients(agent_id),
                "held_facts": tuple(
                    _fact_view(fact, dealt_ids, shared_ids) for fact in hand
                ),
                "received": tuple(
                    _fact_view(fact, dealt_ids, shared_ids)
                    for fact in received.get(agent_id, [])
                ),
                "belief": option_belief(hand, self.config.options),
            }
        return observations

    def _held_fact(self, agent_id: str, fact_id: object) -> Fact:
        """Return a fact the agent currently holds."""
        if not isinstance(fact_id, str) or not fact_id:
            raise ValueError("fact_id must be a non-empty string")
        for fact in self._hands[agent_id]:
            if fact.fact_id == fact_id:
                return fact
        raise ValueError("the agent can disclose only a held fact")

    def _held_snapshot(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        """Return held fact ids for every agent."""
        return tuple(
            (
                agent_id,
                tuple(fact.fact_id for fact in self._hands[agent_id]),
            )
            for agent_id in self.config.agents
        )

    def _require_agents(self, actions: dict[str, dict[str, object]]) -> None:
        """Reject a step that misses an agent."""
        if set(actions) != set(self.config.agents):
            raise ValueError("the step requires one action per agent")

    def _append(self, event: RecorderInputEvent) -> None:
        """Store one event and advance the total order."""
        self._events.append(event)
        self._sequence_index += 1


def option_belief(
    held: tuple[Fact, ...] | list[Fact],
    options: tuple[str, ...],
) -> tuple[float, ...]:
    """Return the declared softmax of held-fact scores over the options.

    The temperature is fixed at one.

    Args:
        held: Facts the agent currently holds.
        options: Ordered option alphabet.

    Returns:
        One probability per option, in alphabet order.
    """
    scores = [
        sum(fact.weight for fact in held if fact.option == option)
        for option in options
    ]
    peak = max(scores) if scores else 0
    weights = [math.exp(score - peak) for score in scores]
    total = math.fsum(weights)
    return tuple(weight / total for weight in weights)


def majority(votes: object, options: tuple[str, ...]) -> str:
    """Return the majority option, breaking ties by option order.

    Args:
        votes: Option names, one per voter.
        options: Ordered option alphabet.

    Returns:
        The selected option.
    """
    counts = {option: 0 for option in options}
    for vote in votes:
        counts[str(vote)] += 1
    best = max(counts.values())
    for option in options:
        if counts[option] == best:
            return option
    return options[0]


def run_episode(
    seed: int,
    config: HiddenProfileConfig = DEFAULT_CONFIG,
    allocation: Mapping[str, Sequence[str]] | None = None,
) -> HiddenProfileEpisode:
    """Run one scripted Hidden Profile episode.

    Args:
        seed: Integer seed for the private-fact deal.
        config: Hidden profile configuration.
        allocation: Optional private-fact ids already assigned to each agent.

    Returns:
        The scoring record and the ordered events.
    """
    from .policies import scripted_policy

    rules = HiddenProfileRules(config)
    observations = rules.reset(seed=seed, allocation=allocation)
    policies = {
        agent_id: scripted_policy(agent_id)
        for agent_id in rules.agents
    }
    for _ in range(config.horizon + 1):
        actions = {
            agent_id: policies[agent_id](
                {"inputs": {"observation": observation}}
            )["choice"]["action"]
            for agent_id, observation in observations.items()
        }
        result = rules.step(actions)
        observations = result["observations"]
        if all(result["done"].values()):
            break
    return rules.episode()


def _deal(
    config: HiddenProfileConfig,
    seed: int,
    correct: str,
) -> tuple[dict[str, list[Fact]], dict[str, tuple[str, ...]]]:
    """Deal private facts so no agent starts knowing the correct option."""
    decisive = [
        fact
        for fact in config.facts
        if not fact.shared and fact.option == correct
    ]
    others = [
        fact
        for fact in config.facts
        if not fact.shared and fact.option != correct
    ]
    generator = random.Random(seed)
    generator.shuffle(decisive)
    generator.shuffle(others)
    order = list(config.agents)
    generator.shuffle(order)
    return _assign_private_facts(config, order, decisive, others, correct)


def _assign_private_facts(
    config: HiddenProfileConfig,
    order: Sequence[str],
    decisive: Sequence[Fact],
    others: Sequence[Fact],
    correct: str,
) -> tuple[dict[str, list[Fact]], dict[str, tuple[str, ...]]]:
    """Assign private facts in shuffled order without revealing the answer."""
    shared = [fact for fact in config.facts if fact.shared]
    hands = {agent_id: list(shared) for agent_id in config.agents}
    dealt = {agent_id: [] for agent_id in config.agents}
    for index, fact in enumerate(decisive):
        agent_id = order[index % len(order)]
        hands[agent_id].append(fact)
        dealt[agent_id].append(fact.fact_id)
    for fact in others:
        placed = False
        for agent_id in order:
            candidate = hands[agent_id] + [fact]
            if unique_leader(candidate, config.options) != correct:
                hands[agent_id].append(fact)
                dealt[agent_id].append(fact.fact_id)
                placed = True
                break
        if not placed:
            raise ValueError("no safe agent can hold the private fact")
    dealt_ids = {
        agent_id: tuple(sorted(fact_ids))
        for agent_id, fact_ids in dealt.items()
    }
    for agent_id in config.agents:
        hands[agent_id].sort(key=lambda fact: fact.fact_id)
    return hands, dealt_ids


def _hands_from_allocation(
    config: HiddenProfileConfig,
    allocation: Mapping[str, Sequence[str]],
    correct: str,
) -> tuple[dict[str, list[Fact]], dict[str, tuple[str, ...]]]:
    """Build hands from a complete private-fact allocation."""
    if set(allocation) != set(config.agents):
        raise ValueError("allocation must name every agent once")
    private = {
        fact.fact_id: fact
        for fact in config.facts
        if not fact.shared
    }
    shared = [fact for fact in config.facts if fact.shared]
    seen: list[str] = []
    hands: dict[str, list[Fact]] = {}
    dealt: dict[str, tuple[str, ...]] = {}
    for agent_id in config.agents:
        fact_ids = allocation[agent_id]
        if isinstance(fact_ids, str) or not isinstance(fact_ids, Sequence):
            raise ValueError("allocation must list fact ids for each agent")
        if any(fact_id not in private for fact_id in fact_ids):
            raise ValueError("allocation must name each private fact")
        seen.extend(fact_ids)
        ordered = tuple(sorted(fact_ids))
        dealt[agent_id] = ordered
        hands[agent_id] = list(shared) + [private[fact_id] for fact_id in ordered]
        hands[agent_id].sort(key=lambda fact: fact.fact_id)
        if unique_leader(hands[agent_id], config.options) == correct:
            raise ValueError("allocation lets one agent identify the correct option")
    if sorted(seen) != sorted(private):
        raise ValueError("allocation must assign each private fact once")
    return hands, dealt


def _fact_view(
    fact: Fact,
    dealt_ids: set[str],
    shared_ids: set[str],
) -> dict[str, object]:
    """Return the fact fields an agent is allowed to see."""
    if fact.fact_id in shared_ids:
        origin = "shared"
    elif fact.fact_id in dealt_ids:
        origin = "dealt"
    else:
        origin = "received"
    return {
        "fact_id": fact.fact_id,
        "option": fact.option,
        "weight": fact.weight,
        "origin": origin,
    }


def _recipient_set(
    recipients: object,
    config: HiddenProfileConfig,
    sender_id: str,
) -> frozenset[str]:
    """Validate the recipients named by a disclosure."""
    if isinstance(recipients, str) or not isinstance(recipients, (tuple, list, frozenset)):
        raise ValueError("recipients must name other agents")
    recipient_ids = frozenset(recipients)
    if any(recipient_id not in config.agents for recipient_id in recipient_ids):
        raise ValueError("recipients must name configured agents")
    if sender_id in recipient_ids:
        raise ValueError("the sender cannot be a recipient")
    return recipient_ids
