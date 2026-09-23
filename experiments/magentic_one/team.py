"""Run five Magentic-One roles on a Session.

The orchestrator asks WebSurfer, then FileSurfer, then accepts the web code.
A supplied specialist answers through on_messages.
Coder and ComputerTerminal stay idle.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from doagent import Session

from experiments.attribution.baselines.protocol import StepCollector, notify

from experiments.magentic_one.query import (
    CODER,
    COMPUTER_TERMINAL,
    FILE_CODE,
    FILE_SURFER,
    FROZEN_QUERY,
    ORCHESTRATOR,
    SPECIALISTS,
    WEB_CODE,
    WEB_SURFER,
    gold_record,
)
from experiments.magentic_one.specialists import specialist_policy_factory


class TurnEnv:
    """Share one query with the five agents."""

    def __init__(self, query: Dict[str, Any]) -> None:
        """Store the query and the agent names.

        Args:
            query:
                Query id and text.
        """
        self.query = dict(query)
        self.agents: List[str] = [ORCHESTRATOR, *SPECIALISTS]

    def reset(self, *, seed: int | None = None) -> Dict[str, Dict[str, Any]]:
        """Return the query as each agent's first observation.

        Args:
            seed:
                Ignored.

        Returns:
            One observation per agent.
            Each observation holds the query.
        """
        obs = {"query": dict(self.query)}
        return {agent_id: dict(obs) for agent_id in self.agents}

    def step(self, actions: Dict[str, Any]) -> Dict[str, Any]:
        """Return the query again, together with the actions just taken.

        Args:
            actions:
                Actions submitted on this step.

        Returns:
            Observations, zero rewards, and done false for every agent.
        """
        obs = {
            agent_id: {"query": dict(self.query), "last_actions": dict(actions)}
            for agent_id in self.agents
        }
        rewards = {agent_id: 0.0 for agent_id in self.agents}
        done = {agent_id: False for agent_id in self.agents}
        return {"observations": obs, "rewards": rewards, "done": done}


def orchestrator_policy_factory(params: Dict[str, Any]):
    """Build a policy that assigns WebSurfer, then accepts the report.

    Args:
        params:
            Query text used in the assignment.

    Returns:
        A decide callable.
    """
    query = params.get("query") or FROZEN_QUERY

    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        """Assign the next specialist, or accept the web code once both reports exist.

        Args:
            request:
                Decision request.
                A web_result and a file_result in inputs select the accept action.

        Returns:
            An assign choice carrying the task ledger, or an accept choice carrying the progress ledger.
        """
        inputs = request.get("inputs") or {}
        web_result = inputs.get("web_result")
        file_result = inputs.get("file_result")
        web_fact = web_result.get("fact") if isinstance(web_result, dict) else None
        file_fact = file_result.get("fact") if isinstance(file_result, dict) else None
        text = query.get("text", "")
        if web_fact and file_fact:
            return {
                "choice": {
                    "status": "act",
                    "action": {
                        "type": "accept",
                        "fact": web_fact,
                        "is_complete": True,
                        "reason": f"The shelf code is {web_fact}.",
                        "next_agent": None,
                        "stall_count": 0,
                    },
                },
                "explanation": f"The shelf code is {web_fact}.",
            }
        if web_fact:
            return {
                "choice": {
                    "status": "act",
                    "action": {
                        "type": "assign",
                        "assignee": FILE_SURFER,
                        "instruction": text,
                        "facts": [],
                        "guesses": [],
                        "plan": ["Read the warehouse file."],
                        "version": 1,
                    },
                },
                "explanation": "FileSurfer should read the warehouse file for crate 4817.",
            }
        return {
            "choice": {
                "status": "act",
                "action": {
                    "type": "assign",
                    "assignee": WEB_SURFER,
                    "instruction": text,
                    "facts": [],
                    "guesses": [],
                    "plan": [
                        "Ask WebSurfer for the shelf code.",
                        "Ask FileSurfer to read the warehouse file.",
                        "Accept a code only when the two agree.",
                    ],
                    "version": 1,
                },
            },
            "explanation": (
                "WebSurfer should look up the shelf code. "
                "FileSurfer should then read the warehouse file."
            ),
        }

    return decide


def web_surfer_policy_factory(params: Dict[str, Any]):
    """Build a policy that reports the web shelf code.

    Args:
        params:
            wrong_fact to report.

    Returns:
        A decide callable.
    """
    fact = params.get("wrong_fact")

    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        """Report the web shelf code.

        Args:
            request:
                Decision request with the assignment in inputs.

        Returns:
            A web result choice, plus a short explanation.
        """
        return {
            "choice": {
                "status": "act",
                "action": {"type": "web_result", "fact": fact},
            },
            "explanation": f"The listing shows shelf code {fact}.",
        }

    return decide


def file_surfer_policy_factory(params: Dict[str, Any]):
    """Build a policy that reports the warehouse file code.

    Args:
        params:
            ledger_fact to report.

    Returns:
        A decide callable.
    """
    fact = params.get("ledger_fact")

    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        """Report the code stored in the warehouse file.

        Args:
            request:
                Decision request with the assignment in inputs.

        Returns:
            A file result choice, plus a short explanation.
        """
        return {
            "choice": {
                "status": "act",
                "action": {"type": "file_result", "fact": fact},
            },
            "explanation": f"The warehouse file lists shelf code {fact}.",
        }

    return decide


def idle_policy_factory(params: Dict[str, Any]):
    """Build a policy that records an idle action.

    Args:
        params:
            Unused.

    Returns:
        A decide callable.
    """

    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        """Return an idle action.

        Args:
            request:
                Decision request.

        Returns:
            An idle choice, plus a short explanation.
        """
        return {
            "choice": {"status": "act", "action": {"type": "idle"}},
            "explanation": "No assignment for this agent.",
        }

    return decide


def build_session(storage: str, output_base: str, logging_level: int = 2) -> Session:
    """Create a federated session for the five-agent team.

    Args:
        storage:
            Either memory or file.
        output_base:
            Root folder for file-backed runs.
        logging_level:
            Session recording level, 0, 1, or 2.

    Returns:
        An open session ready to run the team.

    Raises:
        ValueError:
            If storage is outside memory and file.
    """
    config: Dict[str, Any] = {
        "run_config": {"logging_level": logging_level},
        "topology": {"mode": "federated"},
        "hub_id": ORCHESTRATOR,
        "participation": True,
        "policies": {
            "orchestrator": orchestrator_policy_factory,
            "web_surfer": web_surfer_policy_factory,
            "file_surfer": file_surfer_policy_factory,
            "specialist": specialist_policy_factory,
            "idle": idle_policy_factory,
        },
    }
    if storage == "memory":
        config["shared_data"] = {"type": "memory"}
    elif storage == "file":
        config["shared_data"] = {"type": "file"}
        config["scenario_name"] = "magentic_one"
        config["output_base"] = output_base
    else:
        raise ValueError(f"Unknown storage {storage!r}")
    return Session.from_config(config)


def run_magentic_team(
    query: Dict[str, Any] | None = None,
    plant: Dict[str, Any] | None = None,
    collectors: Iterable[StepCollector] = (),
    specialists: Dict[str, Any] | None = None,
    *,
    storage: str = "memory",
    output_base: str = "./output",
    logging_level: int = 2,
) -> Dict[str, Any]:
    """Run assign, web report, file report, and accept on a Session.

    The session is closed before this function returns.
    Collectors are notified after each decision.

    Args:
        query:
            Query id and text.
            The frozen crate query is used when this is omitted.
        plant:
            Optional wrong_fact and ledger_fact.
            The mode must be accept_last.
        collectors:
            Observers notified after each decision.
            No observers are attached when this is omitted.
        specialists:
            Optional long-lived agents keyed by agent id.
            A supplied agent replaces the stand-in policy for that id.
        storage:
            Either memory or file.
        output_base:
            Root folder for file-backed runs.
        logging_level:
            Session recording level, 0, 1, or 2.

    Returns:
        The session, gold labels, the assignment, both reported codes, and any collector packs.

    Raises:
        ValueError:
            If the plant mode is outside accept_last, or storage is unknown.
    """
    task = dict(query or FROZEN_QUERY)
    spec = dict(plant or {})
    spec.setdefault("mode", "accept_last")
    spec.setdefault("wrong_fact", WEB_CODE)
    spec.setdefault("ledger_fact", FILE_CODE)
    if spec["mode"] != "accept_last":
        raise ValueError("This run supports accept_last.")
    session = build_session(storage, output_base, logging_level=logging_level)
    try:
        return _run_magentic_team(
            session,
            task,
            spec,
            tuple(collectors),
            specialists or {},
        )
    finally:
        session.close()


_SPECIALIST_ACTION = {
    WEB_SURFER: "web_result",
    FILE_SURFER: "file_result",
    CODER: "code_result",
    COMPUTER_TERMINAL: "shell_result",
}


def _agent_policy(
    agent_id: str,
    plant: Dict[str, Any],
    specialists: Dict[str, Any],
) -> Dict[str, Any]:
    """Choose the policy config for one agent.

    Args:
        agent_id:
            Registered agent id.
        plant:
            wrong_fact, ledger_fact, and mode.
        specialists:
            Long-lived agents keyed by agent id.

    Returns:
        A policy name and its params.
    """
    supplied = specialists.get(agent_id)
    if supplied is not None:
        return {
            "name": "specialist",
            "params": {
                "agent": supplied,
                "action_type": _SPECIALIST_ACTION[agent_id],
            },
        }
    if agent_id == WEB_SURFER:
        return {"name": "web_surfer", "params": {"wrong_fact": plant["wrong_fact"]}}
    if agent_id == FILE_SURFER:
        return {"name": "file_surfer", "params": {"ledger_fact": plant["ledger_fact"]}}
    return {"name": "idle", "params": {}}


def _close_policies(agents: Dict[str, Any]) -> None:
    """Close each policy that keeps a specialist event loop.

    Args:
        agents:
            Session agents created for this run.
    """
    for agent in agents.values():
        closer = getattr(getattr(agent, "_policy", None), "close", None)
        if callable(closer):
            closer()


def _run_magentic_team(
    session: Session,
    query: Dict[str, Any],
    plant: Dict[str, Any],
    collectors: tuple[StepCollector, ...] = (),
    specialists: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Run assign, web report, file report, and accept on an open session.

    Args:
        session:
            Open session that already has policies registered.
        query:
            Query id and text.
        plant:
            wrong_fact, ledger_fact, and mode.
        collectors:
            Observers notified after each decision.
        specialists:
            Long-lived agents keyed by agent id.

    Returns:
        The session, gold labels, the assignment, both reported codes, and any collector packs.
    """
    env = session.wrap_env(TurnEnv(query), env_actor="turn_env")
    session.register_participant(ORCHESTRATOR, capabilities=["plan", "assign"])
    session.register_participant(WEB_SURFER, capabilities=["browser"])
    session.register_participant(FILE_SURFER, capabilities=["files"])
    session.register_participant(CODER, capabilities=["code"])
    session.register_participant(COMPUTER_TERMINAL, capabilities=["shell"])
    supplied = specialists or {}
    agents = session.create_agents(
        [
            {
                "id": ORCHESTRATOR,
                "policy": {"name": "orchestrator", "params": {"query": query}},
            },
            {"id": WEB_SURFER, "policy": _agent_policy(WEB_SURFER, plant, supplied)},
            {"id": FILE_SURFER, "policy": _agent_policy(FILE_SURFER, plant, supplied)},
            {"id": CODER, "policy": _agent_policy(CODER, plant, supplied)},
            {
                "id": COMPUTER_TERMINAL,
                "policy": _agent_policy(COMPUTER_TERMINAL, plant, supplied),
            },
        ],
        goal="answer-the-query",
    )
    observations = env.reset()
    assign_inputs = {"query": query, "observation": observations[ORCHESTRATOR]}
    assigned = agents[ORCHESTRATOR].decide(
        observations[ORCHESTRATOR],
        0,
        inputs=assign_inputs,
    )
    notify(
        collectors,
        step=0,
        agent=ORCHESTRATOR,
        request={"inputs": assign_inputs},
        response=assigned["response"],
    )
    assignment = assigned["action"]
    env.step({ORCHESTRATOR: assignment})
    web_inputs = {"assignment": assignment, "observation": observations[WEB_SURFER]}
    reported = agents[WEB_SURFER].decide(
        observations[WEB_SURFER],
        1,
        inputs=web_inputs,
    )
    notify(
        collectors,
        step=1,
        agent=WEB_SURFER,
        request={"inputs": web_inputs},
        response=reported["response"],
    )
    web_result = reported["action"]
    env.step({WEB_SURFER: web_result})
    file_assign_inputs = {
        "query": query,
        "web_result": web_result,
        "observation": observations[ORCHESTRATOR],
    }
    file_assigned = agents[ORCHESTRATOR].decide(
        observations[ORCHESTRATOR],
        2,
        inputs=file_assign_inputs,
    )
    notify(
        collectors,
        step=2,
        agent=ORCHESTRATOR,
        request={"inputs": file_assign_inputs},
        response=file_assigned["response"],
    )
    file_assignment = file_assigned["action"]
    env.step({ORCHESTRATOR: file_assignment})
    file_inputs = {
        "assignment": file_assignment,
        "observation": observations[FILE_SURFER],
    }
    filed = agents[FILE_SURFER].decide(
        observations[FILE_SURFER],
        3,
        inputs=file_inputs,
    )
    notify(
        collectors,
        step=3,
        agent=FILE_SURFER,
        request={"inputs": file_inputs},
        response=filed["response"],
    )
    file_result = filed["action"]
    env.step({FILE_SURFER: file_result})
    accept_inputs = {
        "query": query,
        "web_result": web_result,
        "file_result": file_result,
        "observation": observations[ORCHESTRATOR],
    }
    accepted = agents[ORCHESTRATOR].decide(
        observations[ORCHESTRATOR],
        4,
        inputs=accept_inputs,
    )
    notify(
        collectors,
        step=4,
        agent=ORCHESTRATOR,
        request={"inputs": accept_inputs},
        response=accepted["response"],
    )
    env.step({ORCHESTRATOR: accepted["action"]})
    gold = gold_record(query, plant)
    gold["run_id"] = session.run_id
    try:
        return {
            "session": session,
            "gold": gold,
            "assignment": assignment,
            "web_result": web_result,
            "file_result": file_result,
            "packs": {item.name: item.steps() for item in collectors},
        }
    finally:
        _close_policies(agents)
