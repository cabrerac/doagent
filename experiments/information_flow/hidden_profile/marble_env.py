"""Expose Hidden Profile rules as a MARBLE environment."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from experiments.information_flow.hidden_profile.marble_support import prepare_marble

prepare_marble()

from marble.environments.base_env import BaseEnvironment
from marble.utils.logger import get_logger

from experiments.information_flow.hidden_profile.rules import (
    DEFAULT_CONFIG,
    HiddenProfileRules,
)


class HiddenProfileEnv(BaseEnvironment):
    """Forward disclosures and votes to the shared rules.

    Args:
        name: Name of this environment.
        config: MARBLE environment configuration.
            The seed field selects the private-fact deal.
        rules: Shared rules.
            Defaults to the reference configuration.
    """

    def __init__(
        self,
        name: str,
        config: dict,
        rules: HiddenProfileRules | None = None,
    ) -> None:
        """Store the rules and wait for a deal."""
        super().__init__(name, config)
        profile = config.get("hidden_profile")
        if rules is not None:
            self.rules = rules
        elif profile is None:
            self.rules = HiddenProfileRules(DEFAULT_CONFIG)
        else:
            self.rules = HiddenProfileRules(profile)
        self.logger = get_logger("HiddenProfileEnv")
        self._observations: dict = {}

    def begin(
        self,
        seed: int,
        allocation: Mapping[str, Sequence[str]] | None = None,
    ) -> dict:
        """Deal the facts and remember each agent's view.

        Args:
            seed: Integer seed for the private-fact deal.
            allocation: Optional private-fact ids already assigned to each agent.
                When provided, the seed only labels the episode.

        Returns:
            One observation mapping per agent.
        """
        self._observations = self.rules.reset(seed=seed, allocation=allocation)
        self.done = False
        dealt = []
        for agent_id, observation in self._observations.items():
            fact_ids = [
                str(fact["fact_id"])
                for fact in observation["held_facts"]
                if fact["origin"] == "dealt"
            ]
            dealt.append(f"{agent_id}={','.join(fact_ids)}")
        self.logger.info("Dealt the private facts. " + " ".join(dealt))
        return self._observations

    def observation_for(self, agent_id: str) -> dict:
        """Return the view stored for one agent.

        Args:
            agent_id: Identifier of the agent.

        Returns:
            That agent's current observation.

        Raises:
            KeyError: The agent has no stored view.
        """
        return self._observations[agent_id]

    def play_round(self, actions: dict) -> dict:
        """Deliver one round of choices through the rules.

        Args:
            actions: Agent identifier to that agent's action.

        Returns:
            The rules' step result.
        """
        result = self.rules.step(actions)
        self._observations = result["observations"]
        self.done = all(result["done"].values())
        self.logger.info("Applied one round of choices.")
        return result
