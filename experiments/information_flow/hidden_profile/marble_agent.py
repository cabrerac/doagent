"""Choose Hidden Profile actions as a MARBLE agent."""

from __future__ import annotations

from experiments.information_flow.hidden_profile.marble_support import prepare_marble

prepare_marble()

from marble.agent.base_agent import BaseAgent
from marble.utils.logger import get_logger

from experiments.information_flow.hidden_profile.marble_env import HiddenProfileEnv
from experiments.information_flow.hidden_profile.policies import scripted_policy


class HiddenProfileAgent(BaseAgent):
    """Call the shared scripted policy instead of a language model.

    Args:
        config: MARBLE agent configuration.
            It must include agent_id.
        env: Hidden Profile environment that holds the current views.
    """

    def __init__(self, config: dict, env: HiddenProfileEnv) -> None:
        """Register the agent and keep a logger under its own name."""
        super().__init__(config, env)
        self.env: HiddenProfileEnv = env
        self._policy = scripted_policy(self.agent_id)
        self.logger = get_logger(f"HiddenProfileAgent.{self.agent_id}")
        self.logger.propagate = False
        self.logger.info("Agent is ready.")

    def act(self, task: str) -> tuple[dict, list]:
        """Disclose or vote from the view this agent currently holds.

        Args:
            task: Task text supplied by the engine.
                The scripted policy does not read it.

        Returns:
            The chosen action, and an empty communication list.
        """
        del task
        observation = self.env.observation_for(self.agent_id)
        choice = self._policy({"inputs": {"observation": observation}})
        action = choice["choice"]["action"]
        self.logger.info(_action_line(action))
        return action, []


def _action_line(action: dict) -> str:
    """Describe one choice on a single log line."""
    kind = action.get("kind")
    if kind == "disclose":
        fact_id = action.get("fact_id") or ""
        recipients = action.get("recipients") or ()
        names = ",".join(sorted(str(recipient) for recipient in recipients))
        return f"Chose an action. kind=disclose fact={fact_id} recipients={names}"
    if kind == "vote":
        return f"Chose an action. kind=vote option={action.get('option')}"
    return "Chose an action."
