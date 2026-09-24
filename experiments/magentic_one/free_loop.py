"""Run an orchestrator that chooses the next speaker until it stops.

The session records each decision.
WebSurfer answers through on_messages.
The dataset step index is not copied onto this run.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from doagent import Session

from experiments.attribution.baselines.protocol import StepCollector, notify
from experiments.attribution.projections import write_attribution_artifacts
from experiments.magentic_one.log36 import (
    LOG36_QUERY,
    MAX_STALLS,
    MAX_TURNS,
    ROSTER,
    SPEAKER_NAME,
    gold_record,
)
from experiments.magentic_one.query import ORCHESTRATOR, WEB_SURFER
from experiments.magentic_one.specialists import specialist_policy_factory
from experiments.magentic_one.team import _close_policies


class PairEnv:
    """Share one query with the orchestrator and WebSurfer."""

    def __init__(self, query: Dict[str, Any]) -> None:
        """Store the query and the two agent names.

        Args:
            query:
                Query id and text.
        """
        self.query = dict(query)
        self.agents = list(ROSTER)

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


def ledger_policy_factory(params: Dict[str, Any]):
    """Build a policy that keeps a Magentic-One ledger.

    Args:
        params:
            model_client calls the proxy.
            task is the user request.
            team is the one-line team description.
            names lists the speakers the ledger may choose.
            max_json_retries is how many times to ask for a valid ledger.

    Returns:
        A decide callable.
        The callable has a close method that shuts its event loop.

    Raises:
        ValueError:
            If model_client or task is missing.
    """
    client = params.get("model_client")
    task = str(params.get("task") or "")
    if client is None or not task:
        raise ValueError("A ledger policy needs a model client and a task.")
    team = str(params.get("team") or f"{SPEAKER_NAME}: browses the web.")
    names = list(params.get("names") or [SPEAKER_NAME])
    max_json_retries = int(params.get("max_json_retries") or 10)
    loop = asyncio.new_event_loop()
    messages: List[Any] = []
    facts = ""
    plan = ""

    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        """Take one ledger step and return it as an action.

        Args:
            request:
                Decision request.
                phase selects the ledger step.
                latest_reply is appended before a progress step.

        Returns:
            An action holding the fact sheet, the plan, the progress ledger, or the final answer.

        Raises:
            ValueError:
                If phase is unknown, or the progress ledger never parses.
        """
        nonlocal facts, plan
        inputs = request.get("inputs") or {}
        phase = str(inputs.get("phase") or "")
        latest = inputs.get("latest_reply")
        if latest:
            messages.append(_user(str(latest), SPEAKER_NAME))
        if phase == "facts":
            facts = _complete(client, [_user(_facts_prompt(task), ORCHESTRATOR)], loop)
            return _text_action("facts", facts, "Gathered the fact sheet.")
        if phase == "plan":
            plan = _complete(
                client,
                [
                    _user(_facts_prompt(task), ORCHESTRATOR),
                    _assistant(facts),
                    _user(_plan_prompt(team), ORCHESTRATOR),
                ],
                loop,
            )
            _install_ledger(messages, task, team, facts, plan)
            return _text_action("plan", plan, "Wrote the plan.")
        if phase == "update_facts":
            facts = _complete(
                client,
                [*messages, _user(_facts_update_prompt(task, facts), ORCHESTRATOR)],
                loop,
            )
            messages.append(_assistant(facts))
            return _text_action("facts", facts, "Updated the fact sheet.")
        if phase == "update_plan":
            plan = _complete(
                client,
                [*messages, _user(_plan_update_prompt(team), ORCHESTRATOR)],
                loop,
            )
            _install_ledger(messages, task, team, facts, plan)
            return _text_action("plan", plan, "Updated the plan.")
        if phase == "progress":
            ledger = _progress_ledger(
                client,
                messages,
                _progress_prompt(task, team, names),
                names,
                loop,
                max_json_retries,
            )
            instruction = str(ledger["instruction_or_question"]["answer"])
            messages.append(_assistant(instruction))
            reason = str(ledger["is_request_satisfied"]["reason"])
            return {
                "choice": {
                    "status": "act",
                    "action": {
                        "type": "progress_ledger",
                        "ledger": ledger,
                        "instruction": instruction,
                        "next_agent": ledger["next_speaker"]["answer"],
                        "is_complete": _as_bool(ledger["is_request_satisfied"]["answer"]),
                    },
                },
                "explanation": reason,
            }
        if phase == "final":
            answer = _complete(
                client,
                [*messages, _user(_final_prompt(task), ORCHESTRATOR)],
                loop,
            )
            messages.append(_assistant(answer))
            return {
                "choice": {
                    "status": "act",
                    "action": {
                        "type": "final_answer",
                        "text": answer,
                        "reason": str(inputs.get("reason") or ""),
                    },
                },
                "explanation": "Stated the final answer.",
            }
        raise ValueError(f"Unknown ledger phase {phase!r}.")

    def close() -> None:
        """Close the event loop used for model calls."""
        if not loop.is_closed():
            loop.close()

    decide.close = close
    return decide


def run_free_team(
    query: Dict[str, Any] | None = None,
    *,
    model_client: Any,
    web_surfer: Any,
    collectors: Iterable[StepCollector] = (),
    max_turns: int = MAX_TURNS,
    max_stalls: int = MAX_STALLS,
    storage: str = "memory",
    output_base: str = "./output",
    logging_level: int = 2,
    team: str | None = None,
) -> Dict[str, Any]:
    """Run the ledger loop on a Session and close it before returning.

    Args:
        query:
            Query id and text.
            The log 36 question is used when this is omitted.
        model_client:
            Client used for ledger steps.
        web_surfer:
            Specialist that answers through on_messages.
        collectors:
            Observers notified after each decision.
        max_turns:
            Progress steps allowed before the run stops.
        max_stalls:
            Stalls allowed before the plan is rewritten.
        storage:
            Either memory or file.
        output_base:
            Root folder for file-backed runs.
        logging_level:
            Session recording level, 0, 1, or 2.
        team:
            One-line description of WebSurfer.

        Returns:
        The session, unlabeled gold, the final answer, the decision trace, and any written paths.
        The files are written before the browser is closed.

    Raises:
        ValueError:
            If storage is unknown, or the ledger does not parse.
    """
    task = dict(query or LOG36_QUERY)
    session = _build_session(storage, output_base, logging_level)
    sink: Dict[str, Any] = {"agents": {}, "result": None, "partial": None}
    try:
        sink["result"] = _run_free_team(
            session,
            task,
            model_client,
            web_surfer,
            tuple(collectors),
            sink,
            max_turns=max_turns,
            max_stalls=max_stalls,
            team=team,
        )
        return sink["result"]
    finally:
        _save_then_close(session, sink, tuple(collectors))


def write_free_artifacts(result: Dict[str, Any], collectors: Iterable[StepCollector]) -> Dict[str, str]:
    """Write gold, collector packs, and session views for one free-loop run.

    Args:
        result:
            Return value of run_free_team.
        collectors:
            Observers that already recorded the run.

    Returns:
        Written paths keyed by artifact name.
        An empty mapping when the session has no run folder.
    """
    written: Dict[str, str] = {}
    run_path = result["session"].run_path
    if not run_path:
        return written
    root = Path(run_path)
    gold_path = root / "gold.json"
    gold_path.write_text(
        json.dumps(result["gold"], indent=2) + "\n",
        encoding="utf-8",
    )
    written["gold"] = str(gold_path)
    analysis = root / "analysis" / "attribution"
    for collector in collectors:
        written[collector.name] = collector.write(analysis / collector.filename)
    written.update(write_attribution_artifacts(result["session"], root))
    return written


def _save_then_close(
    session: Session,
    sink: Dict[str, Any],
    collectors: tuple[StepCollector, ...],
) -> None:
    """Flush the log, then close the browser.

    Args:
        session:
            Session that holds the run.
        sink:
            Result, partial result, and the agents to close.
        collectors:
            Observers that already recorded the run.
    """
    result = sink.get("result") or sink.get("partial")
    try:
        session.close()
        if result is None:
            return
        written = write_free_artifacts(result, collectors)
        result["artifact_paths"] = written
        for name, path in written.items():
            print(f"{name} written to {path}", flush=True)
    finally:
        print("Closing the browser.", flush=True)
        try:
            _close_policies(sink.get("agents") or {})
        except Exception as exc:
            print(f"Browser close failed: {exc}", flush=True)


def _run_free_team(
    session: Session,
    query: Dict[str, Any],
    model_client: Any,
    web_surfer: Any,
    collectors: tuple[StepCollector, ...],
    sink: Dict[str, Any],
    *,
    max_turns: int,
    max_stalls: int,
    team: str | None,
) -> Dict[str, Any]:
    """Run facts, plan, and progress steps until the ledger says stop.

    Args:
        session:
            Open session that already has policies registered.
        query:
            Query id and text.
        model_client:
            Client used for ledger steps.
        web_surfer:
            Specialist that answers through on_messages.
        collectors:
            Observers notified after each decision.
        max_turns:
            Progress steps allowed before the run stops.
        max_stalls:
            Stalls allowed before the plan is rewritten.
        sink:
            Collects the agents and a partial result when the loop stops early.
        team:
            One-line description of WebSurfer.

    Returns:
        The session, unlabeled gold, the final answer, and the decision trace.
    """
    env = session.wrap_env(PairEnv(query), env_actor="turn_env")
    session.register_participant(ORCHESTRATOR, capabilities=["plan", "assign"])
    session.register_participant(WEB_SURFER, capabilities=["browser"])
    description = team or f"{SPEAKER_NAME}: browses the web and reports the page."
    agents = session.create_agents(
        [
            {
                "id": ORCHESTRATOR,
                "policy": {
                    "name": "ledger",
                    "params": {
                        "model_client": model_client,
                        "task": query.get("text") or "",
                        "team": description,
                        "names": [SPEAKER_NAME],
                    },
                },
            },
            {
                "id": WEB_SURFER,
                "policy": {
                    "name": "specialist",
                    "params": {"agent": web_surfer, "action_type": "web_result"},
                },
            },
        ],
        goal="answer-the-query",
    )
    sink["agents"] = agents
    observations = env.reset()
    trace: List[Dict[str, Any]] = []
    step = 0
    latest_reply: Optional[str] = None

    def one(agent_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Record one decision and advance the shared clock.

        Args:
            agent_id:
                Agent that decides.
            inputs:
                Inputs stored with the decision.

        Returns:
            The decide result.
        """
        nonlocal step
        print(
            f"step {step} {agent_id}: starting {_step_label(inputs)}",
            flush=True,
        )
        payload = {**inputs, "observation": observations[agent_id]}
        decided = agents[agent_id].decide(observations[agent_id], step, inputs=payload)
        notify(
            collectors,
            step=step,
            agent=agent_id,
            request={"inputs": payload},
            response=decided["response"],
        )
        action = decided["action"]
        env.step({agent_id: action})
        trace.append({"step": step, "agent": agent_id, "action": action})
        print(f"step {step} {agent_id}: {_step_summary(action)}", flush=True)
        step += 1
        return decided

    try:
        one(ORCHESTRATOR, {"phase": "facts", "query": query})
        one(ORCHESTRATOR, {"phase": "plan", "query": query})
        rounds = 0
        stalls = 0
        final_action: Optional[Dict[str, Any]] = None
        while rounds < max_turns:
            rounds += 1
            progress_inputs: Dict[str, Any] = {"phase": "progress", "query": query}
            if latest_reply:
                progress_inputs["latest_reply"] = latest_reply
            progressed = one(ORCHESTRATOR, progress_inputs)
            ledger_action = progressed["action"]
            latest_reply = None
            if ledger_action.get("is_complete"):
                final_action = one(
                    ORCHESTRATOR,
                    {
                        "phase": "final",
                        "query": query,
                        "reason": ledger_action.get("ledger", {})
                        .get("is_request_satisfied", {})
                        .get("reason"),
                    },
                )["action"]
                break
            stalls = _next_stalls(stalls, ledger_action.get("ledger") or {})
            if stalls >= max_stalls:
                one(ORCHESTRATOR, {"phase": "update_facts", "query": query})
                one(ORCHESTRATOR, {"phase": "update_plan", "query": query})
                stalls = 0
                resetter = getattr(agents[WEB_SURFER]._policy, "reset", None)
                if callable(resetter):
                    resetter()
                continue
            reported = one(
                WEB_SURFER,
                {
                    "assignment": {"instruction": ledger_action.get("instruction")},
                    "query": query,
                },
            )
            latest_reply = str((reported["action"] or {}).get("fact") or "")
        else:
            final_inputs = {
                "phase": "final",
                "query": query,
                "reason": "Max rounds reached.",
            }
            if latest_reply:
                final_inputs["latest_reply"] = latest_reply
            final_action = one(ORCHESTRATOR, final_inputs)["action"]
        final_text = None if final_action is None else final_action.get("text")
        gold = gold_record(query, final_answer=final_text, run_id=session.run_id)
        return {
            "session": session,
            "gold": gold,
            "final_answer": final_text,
            "trace": trace,
        }
    except Exception:
        sink["partial"] = {
            "session": session,
            "gold": gold_record(query, final_answer=None, run_id=session.run_id),
            "final_answer": None,
            "trace": list(trace),
        }
        raise


def _step_label(inputs: Dict[str, Any]) -> str:
    """Name the ledger step that is about to run.

    Args:
        inputs:
            Decision inputs.

    Returns:
        A short label for the terminal line.
    """
    labels = {
        "facts": "fact sheet",
        "plan": "plan",
        "update_facts": "fact sheet update",
        "update_plan": "plan update",
        "progress": "progress ledger",
        "final": "final answer",
    }
    phase = inputs.get("phase")
    if isinstance(phase, str) and phase in labels:
        return labels[phase]
    if inputs.get("assignment"):
        return "browser"
    return "decision"


def _step_summary(action: Any) -> str:
    """Shorten one action to a single terminal line.

    Args:
        action:
            Action just recorded.

    Returns:
        One line, trimmed when the text is long.
    """
    if not isinstance(action, dict):
        return _one_line(str(action))
    if action.get("type") == "task_ledger":
        return _one_line(str(action.get("text") or ""))
    if action.get("type") == "progress_ledger":
        instruction = str(action.get("instruction") or "")
        state = "stop" if action.get("is_complete") else "continue"
        return _one_line(f"{state}. {instruction}")
    if action.get("type") == "final_answer":
        return _one_line(str(action.get("text") or ""))
    if action.get("fact"):
        return _one_line(str(action.get("fact")))
    return _one_line(str(action.get("type") or "done"))


def _one_line(text: str, limit: int = 160) -> str:
    """Collapse whitespace and trim a long line.

    Args:
        text:
            Text to show.
        limit:
            Maximum length of the returned line.

    Returns:
        A single line.
    """
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    return flat[: limit - 3] + "..."


def _build_session(storage: str, output_base: str, logging_level: int) -> Session:
    """Create a federated session for the orchestrator and WebSurfer.

    Args:
        storage:
            Either memory or file.
        output_base:
            Root folder for file-backed runs.
        logging_level:
            Session recording level, 0, 1, or 2.

    Returns:
        An open session ready to run the ledger loop.

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
            "ledger": ledger_policy_factory,
            "specialist": specialist_policy_factory,
        },
    }
    if storage == "memory":
        config["shared_data"] = {"type": "memory"}
    elif storage == "file":
        config["shared_data"] = {"type": "file"}
        config["scenario_name"] = "magentic_one_log36"
        config["output_base"] = output_base
    else:
        raise ValueError(f"Unknown storage {storage!r}")
    return Session.from_config(config)


def _next_stalls(stalls: int, ledger: Dict[str, Any]) -> int:
    """Count a stall when the ledger says progress stopped or a loop started.

    Args:
        stalls:
            Stall count before this progress step.
        ledger:
            Parsed progress ledger.

    Returns:
        The updated stall count.
    """
    making = _as_bool((ledger.get("is_progress_being_made") or {}).get("answer"))
    looping = _as_bool((ledger.get("is_in_loop") or {}).get("answer"))
    if not making or looping:
        return stalls + 1
    return max(0, stalls - 1)


def _progress_ledger(
    client: Any,
    messages: List[Any],
    prompt: str,
    names: List[str],
    loop: asyncio.AbstractEventLoop,
    retries: int,
) -> Dict[str, Any]:
    """Ask for a progress ledger until one object parses.

    Args:
        client:
            Model client.
        messages:
            Ledger context so far.
        prompt:
            Progress question.
        names:
            Allowed speaker names.
        loop:
            Event loop for the model call.
        retries:
            How many replies to accept before failing.

    Returns:
        The parsed progress ledger.

    Raises:
        ValueError:
            If no reply parses.
    """
    context = [*messages, _user(prompt, ORCHESTRATOR)]
    last_error = "no reply"
    for _ in range(retries):
        text = _complete(client, context, loop, json_output=True)
        try:
            return _ledger_from_text(text, names)
        except ValueError as exc:
            last_error = str(exc)
            context.append(_assistant(text))
            context.append(_user("Reply with one JSON object only.", ORCHESTRATOR))
    raise ValueError(f"Failed to parse the progress ledger: {last_error}")


def _ledger_from_text(text: str, names: List[str]) -> Dict[str, Any]:
    """Parse one progress ledger and force the only speaker when the team has one.

    Args:
        text:
            Model reply.
        names:
            Allowed speaker names.

    Returns:
        A ledger with boolean answers and a next speaker.

    Raises:
        ValueError:
            If the reply is not one ledger object, or a required field is missing.
    """
    from autogen_core.utils import extract_json_from_str

    found = extract_json_from_str(text)
    if len(found) != 1 or not isinstance(found[0], dict):
        raise ValueError("Progress ledger must be one JSON object.")
    ledger = found[0]
    required = (
        "is_request_satisfied",
        "is_progress_being_made",
        "is_in_loop",
        "instruction_or_question",
        "next_speaker",
    )
    for key in required:
        entry = ledger.get(key)
        if not isinstance(entry, dict) or "answer" not in entry or "reason" not in entry:
            raise ValueError(f"Progress ledger is missing {key}.")
    for key in ("is_request_satisfied", "is_progress_being_made", "is_in_loop"):
        ledger[key]["answer"] = _as_bool(ledger[key]["answer"])
    if len(names) == 1:
        ledger["next_speaker"] = {
            "reason": "The team consists of only one agent.",
            "answer": names[0],
        }
    elif ledger["next_speaker"]["answer"] not in names and not ledger["is_request_satisfied"]["answer"]:
        raise ValueError("Progress ledger named a speaker outside the team.")
    return ledger


def _complete(
    client: Any,
    messages: List[Any],
    loop: asyncio.AbstractEventLoop,
    *,
    json_output: bool = False,
) -> str:
    """Call the model and return the reply text.

    Args:
        client:
            Model client with create.
        messages:
            Prompt messages.
        loop:
            Event loop for an async client.
        json_output:
            Ask for JSON when the client says it can.

    Returns:
        The reply text.
    """
    kwargs: Dict[str, Any] = {}
    info = getattr(client, "model_info", {}) or {}
    if json_output and info.get("json_output"):
        kwargs["json_output"] = True
    result = client.create(messages, **kwargs)
    if asyncio.iscoroutine(result):
        result = loop.run_until_complete(result)
    content = getattr(result, "content", result)
    if isinstance(content, str):
        return content
    return _content_text(content) or str(content)


def _content_text(content: Any) -> str:
    """Join the text parts of a model reply.

    Args:
        content:
            A string, or a list of parts.

    Returns:
        The joined text.
    """
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: List[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and item.get("text"):
            parts.append(str(item["text"]))
        elif getattr(item, "text", None):
            parts.append(str(item.text))
    return "\n".join(parts)


def _as_bool(value: Any) -> bool:
    """Read a ledger answer as a boolean.

    Args:
        value:
            A boolean, or the strings true or false.

    Returns:
        The boolean value.

    Raises:
        ValueError:
            If the value is not a boolean answer.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in {"true", "yes"}:
        return True
    if isinstance(value, str) and value.strip().lower() in {"false", "no"}:
        return False
    raise ValueError(f"Expected a boolean ledger answer, got {value!r}.")


def _install_ledger(
    messages: List[Any],
    task: str,
    team: str,
    facts: str,
    plan: str,
) -> None:
    """Replace the model context with the full task ledger.

    Args:
        messages:
            Context list to replace.
        task:
            User request.
        team:
            Team description.
        facts:
            Current fact sheet.
        plan:
            Current plan.
    """
    messages.clear()
    messages.append(_assistant(_full_ledger_prompt(task, team, facts, plan)))


def _text_action(part: str, text: str, explanation: str) -> Dict[str, Any]:
    """Wrap a fact sheet or a plan as an action.

    Args:
        part:
            facts or plan.
        text:
            Model text.
        explanation:
            Short line stored beside the action.

    Returns:
        A decide response.
    """
    return {
        "choice": {
            "status": "act",
            "action": {"type": "task_ledger", "part": part, "text": text},
        },
        "explanation": explanation,
    }


def _user(content: str, source: str) -> Any:
    """Build a user message for the model client.

    Args:
        content:
            Message text.
        source:
            Speaker name.

    Returns:
        A user message.
    """
    from autogen_core.models import UserMessage

    return UserMessage(content=content, source=source)


def _assistant(content: str) -> Any:
    """Build an assistant message for the model client.

    Args:
        content:
            Message text.

    Returns:
        An assistant message from the orchestrator.
    """
    from autogen_core.models import AssistantMessage

    return AssistantMessage(content=content, source=ORCHESTRATOR)


def _facts_prompt(task: str) -> str:
    """Return the fact-sheet prompt.

    Args:
        task:
            User request.

    Returns:
        The prompt text.
    """
    from autogen_agentchat.teams._group_chat._magentic_one._prompts import (
        ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT,
    )

    return ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT.format(task=task)


def _plan_prompt(team: str) -> str:
    """Return the plan prompt.

    Args:
        team:
            Team description.

    Returns:
        The prompt text.
    """
    from autogen_agentchat.teams._group_chat._magentic_one._prompts import (
        ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT,
    )

    return ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT.format(team=team)


def _full_ledger_prompt(task: str, team: str, facts: str, plan: str) -> str:
    """Return the ledger that starts the inner loop.

    Args:
        task:
            User request.
        team:
            Team description.
        facts:
            Current fact sheet.
        plan:
            Current plan.

    Returns:
        The prompt text.
    """
    from autogen_agentchat.teams._group_chat._magentic_one._prompts import (
        ORCHESTRATOR_TASK_LEDGER_FULL_PROMPT,
    )

    return ORCHESTRATOR_TASK_LEDGER_FULL_PROMPT.format(
        task=task,
        team=team,
        facts=facts,
        plan=plan,
    )


def _progress_prompt(task: str, team: str, names: List[str]) -> str:
    """Return the progress-ledger prompt.

    Args:
        task:
            User request.
        team:
            Team description.
        names:
            Allowed speaker names.

    Returns:
        The prompt text.
    """
    from autogen_agentchat.teams._group_chat._magentic_one._prompts import (
        ORCHESTRATOR_PROGRESS_LEDGER_PROMPT,
    )

    return ORCHESTRATOR_PROGRESS_LEDGER_PROMPT.format(
        task=task,
        team=team,
        names=", ".join(names),
    )


def _facts_update_prompt(task: str, facts: str) -> str:
    """Return the fact-sheet update prompt.

    Args:
        task:
            User request.
        facts:
            Current fact sheet.

    Returns:
        The prompt text.
    """
    from autogen_agentchat.teams._group_chat._magentic_one._prompts import (
        ORCHESTRATOR_TASK_LEDGER_FACTS_UPDATE_PROMPT,
    )

    return ORCHESTRATOR_TASK_LEDGER_FACTS_UPDATE_PROMPT.format(task=task, facts=facts)


def _plan_update_prompt(team: str) -> str:
    """Return the plan update prompt.

    Args:
        team:
            Team description.

    Returns:
        The prompt text.
    """
    from autogen_agentchat.teams._group_chat._magentic_one._prompts import (
        ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT,
    )

    return ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT.format(team=team)


def _final_prompt(task: str) -> str:
    """Return the final-answer prompt.

    Args:
        task:
            User request.

    Returns:
        The prompt text.
    """
    from autogen_agentchat.teams._group_chat._magentic_one._prompts import (
        ORCHESTRATOR_FINAL_ANSWER_PROMPT,
    )

    return ORCHESTRATOR_FINAL_ANSWER_PROMPT.format(task=task)
