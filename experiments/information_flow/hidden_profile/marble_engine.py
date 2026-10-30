"""Run one Hidden Profile round for every agent, in ring order."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import nullcontext
from pathlib import Path

from experiments.information_flow.hidden_profile.marble_support import prepare_marble

prepare_marble()

from marble.configs.config import Config
from marble.graph.agent_graph import AgentGraph
from marble.utils.logger import get_logger

from experiments.information_flow.hidden_profile.marble_agent import HiddenProfileAgent
from experiments.information_flow.hidden_profile.marble_env import HiddenProfileEnv
from experiments.information_flow.hidden_profile.service_trace import ServiceTrace


class HiddenProfileEngine:
    """Ask each agent once per round and forward the choices together.

    The coordinator reads a MARBLE config and keeps the ring order from the rules.

    Args:
        config: MARBLE configuration.
    """

    def __init__(self, config: Config) -> None:
        """Build the environment, the agents, and the agent graph."""
        self.logger = get_logger(self.__class__.__name__)
        self.config = config
        self.task = config.task.get("content", "")
        env_config = dict(config.environment)
        self.environment = HiddenProfileEnv(
            name="hidden_profile",
            config=env_config,
        )
        self.agents = [
            HiddenProfileAgent(agent_config, self.environment)
            for agent_config in config.agents
        ]
        self.graph = AgentGraph(self.agents, config)
        for agent in self.agents:
            agent.set_agent_graph(self.graph)
        self.logger.info("Engine initialized.")

    def start(
        self,
        seed: int,
        allocation: Mapping[str, Sequence[str]] | None = None,
        trace_path: str | Path | None = None,
    ) -> None:
        """Deal one game and play until the vote.

        Args:
            seed: Integer seed for the private-fact deal.
            allocation: Optional private-fact ids already assigned to each agent.
                When provided, the seed only labels the episode.
            trace_path: Optional file for one structured line per engine call.
                The component logs are unchanged.

        Raises:
            ValueError: The agents are not in ring order.
            RuntimeError: The vote was not reached.
        """
        self.logger.info("Engine starting simulation.")
        expected = list(self.environment.rules.agents)
        actual = [agent.agent_id for agent in self.agents]
        if actual != expected:
            raise ValueError("agents must follow the ring order")
        writer = ServiceTrace(trace_path) if trace_path is not None else nullcontext()
        with writer as trace:
            observations = self.environment.begin(seed, allocation)
            if trace is not None:
                trace.deal(observations)
            steps = 0
            limit = self.environment.rules.config.horizon + 1
            while not self.environment.is_done():
                if steps >= limit:
                    raise RuntimeError("the episode did not reach a vote")
                actions = {}
                for agent in self.agents:
                    action, _communication = agent.act(self.task)
                    actions[agent.agent_id] = action
                    if trace is not None:
                        trace.action(agent.agent_id, action, steps)
                self.environment.play_round(actions)
                steps += 1
        self.logger.info("Simulation completed.")
