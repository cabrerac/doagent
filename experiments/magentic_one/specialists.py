"""Wrap a specialist that answers through on_messages.

One event loop stays open so the specialist can keep its tools.
The Session policy returns the reply as an action.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict

from experiments.magentic_one.query import (
    CODER,
    COMPUTER_TERMINAL,
    FILE_SURFER,
    WEB_SURFER,
)


def specialist_policy_factory(params: Dict[str, Any]):
    """Build a policy that asks one specialist and returns its reply.

    Args:
        params:
            agent is the specialist.
            action_type selects the action layout.
            web_result stores the reply as fact.

    Returns:
        A decide callable.
        The callable has a close method that shuts the specialist and its event loop.

    Raises:
        ValueError:
            If agent is missing.
    """
    agent = params.get("agent")
    if agent is None:
        raise ValueError("A specialist policy needs an agent.")
    action_type = str(params.get("action_type") or "report")
    loop = asyncio.new_event_loop()

    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        """Ask the specialist and return its reply as an action.

        Args:
            request:
                Decision request.
                The instruction is read from inputs.

        Returns:
            An action whose text is the specialist reply.
        """
        inputs = request.get("inputs") or {}
        reply = _ask(agent, _instruction(inputs), loop)
        text = _reply_text(reply)
        return {
            "choice": {"status": "act", "action": _action(action_type, text)},
            "explanation": f"Report {text}.",
        }

    def close() -> None:
        """Close the specialist, then close its event loop."""
        if loop.is_closed():
            return
        try:
            closer = getattr(agent, "close", None)
            if callable(closer):
                result = closer()
                if asyncio.iscoroutine(result):
                    loop.run_until_complete(result)
            pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        finally:
            if not loop.is_closed():
                loop.close()

    decide.close = close
    return decide


def build_specialists(
    model_client: Any,
    code_executor: Any,
    *,
    classes: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build the four AutoGen specialists for one run.

    WebSurfer is constructed with a headless browser.

    Args:
        model_client:
            Model client shared by WebSurfer, FileSurfer, and the coder.
        code_executor:
            Executor used by the terminal agent.
        classes:
            Optional replacements for the four AutoGen classes.
            The installed classes are used when this is omitted.

    Returns:
        Specialists keyed by web_surfer, file_surfer, coder, and computer_terminal.

    Raises:
        ImportError:
            If AutoGen is not installed and classes is omitted.
    """
    kinds = _load_specialist_classes() if classes is None else classes
    return {
        WEB_SURFER: kinds["web"](
            "WebSurfer",
            model_client=model_client,
            headless=True,
        ),
        FILE_SURFER: kinds["file"]("FileSurfer", model_client=model_client),
        CODER: kinds["coder"]("Coder", model_client=model_client),
        COMPUTER_TERMINAL: kinds["terminal"](
            "ComputerTerminal",
            code_executor=code_executor,
        ),
    }


def _load_specialist_classes() -> Dict[str, Any]:
    """Import the four AutoGen specialist classes.

    Returns:
        Classes keyed by web, file, coder, and terminal.

    Raises:
        ImportError:
            If the magentic-one extra is not installed.
    """
    try:
        from autogen_agentchat.agents import CodeExecutorAgent
        from autogen_ext.agents.file_surfer import FileSurfer
        from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
        from autogen_ext.agents.web_surfer import MultimodalWebSurfer
    except ImportError as exc:
        raise ImportError(
            "Install the magentic-one extra to construct the AutoGen specialists."
        ) from exc
    return {
        "web": MultimodalWebSurfer,
        "file": FileSurfer,
        "coder": MagenticOneCoderAgent,
        "terminal": CodeExecutorAgent,
    }


def _instruction(inputs: Dict[str, Any]) -> str:
    """Read the instruction the specialist should answer.

    Args:
        inputs:
            Decision inputs.

    Returns:
        The assignment instruction, or the query text when there is no assignment.
    """
    assignment = inputs.get("assignment")
    if isinstance(assignment, dict) and assignment.get("instruction"):
        return str(assignment["instruction"])
    query = inputs.get("query")
    if isinstance(query, dict) and query.get("text"):
        return str(query["text"])
    return ""


def _ask(agent: Any, instruction: str, loop: asyncio.AbstractEventLoop) -> Any:
    """Call on_messages on the specialist's event loop.

    Args:
        agent:
            Specialist with on_messages.
        instruction:
            Text sent as the user message.
        loop:
            Event loop kept for this specialist.

    Returns:
        Whatever on_messages returns.
    """
    result = agent.on_messages([_message(instruction)], _cancellation_token())
    if asyncio.iscoroutine(result):
        return loop.run_until_complete(result)
    return result


def _message(content: str) -> Any:
    """Build the user message passed to on_messages.

    Args:
        content:
            Instruction text.

    Returns:
        An AutoGen text message when that package is installed.
        Otherwise a simple message with the same content.
    """
    try:
        from autogen_agentchat.messages import TextMessage
    except ImportError:
        return SimpleNamespace(content=content, source="orchestrator")
    return TextMessage(content=content, source="orchestrator")


def _cancellation_token() -> Any:
    """Return a cancellation token when AutoGen provides one.

    Returns:
        A cancellation token, or None when AutoGen is not installed.
    """
    try:
        from autogen_core import CancellationToken
    except ImportError:
        return None
    return CancellationToken()


def _reply_text(reply: Any) -> str:
    """Read the text of a specialist reply.

    Args:
        reply:
            Return value of on_messages.

    Returns:
        The reply text.
    """
    chat_message = getattr(reply, "chat_message", None)
    if chat_message is not None and getattr(chat_message, "content", None):
        return str(chat_message.content)
    if getattr(reply, "content", None):
        return str(reply.content)
    return str(reply)


def _action(action_type: str, text: str) -> Dict[str, str]:
    """Build the action stored for one specialist reply.

    Args:
        action_type:
            Action type name.
        text:
            Reply text.

    Returns:
        A web result when the type is web_result.
        Otherwise an action that stores the reply as content.
    """
    if action_type == "web_result":
        return {"type": "web_result", "fact": text}
    return {"type": action_type, "content": text}
