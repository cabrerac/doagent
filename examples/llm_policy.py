"""Generic LLM policy example for DOAgent.

Demonstrates a model-agnostic policy that wraps any LLM callable provided
via per-agent ``tools`` config.  The library captures the LLM call I/O as
a reasoning trace automatically — no tracing code in the policy itself.

The policy:
  - Builds a prompt from the observation and an action-space description.
  - Calls ``request["tools"]["llm"]`` (whatever the user provided).
  - Parses the structured JSON response into a ``choice``.
  - Maps low confidence or explicit "I don't know" to ``status: "abstain"``.
  - Maps parse/API failures to ``status: "error"``.

Usage with ``create_llm_tool``::

    from examples.llm_policy import create_llm_tool, llm_decide_factory

    llm_tool = create_llm_tool()  # reads GEMINI_API_KEY from env (default)

    configs = [
        {
            "id": "agent_0",
            "policy": {"name": "llm_decide", "params": {
                "model": "gemini-2.5-flash",
                "action_space": {0: "stay", 1: "left", 2: "right", 3: "up", 4: "down"},
                "confidence_threshold": 0.4,
            }},
            "tools": {"llm": llm_tool},
        },
    ]

    session = Session.from_config({
        "shared_data": {"type": "memory"},
        "run_config": {"logging_level": 2},
        "policies": {"llm_decide": llm_decide_factory},
    })

Custom prompts::

    def my_prompt_builder(observation, action_space, goal):
        return f"You are exploring a grid. Position: {observation}. Pick an action."

    params = {
        "action_space": {0: "stay", 1: "left", 2: "right"},
        "build_prompt": my_prompt_builder,
    }
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, Optional


# ---------------------------------------------------------------------------
# LLM tool helpers (example code, not part of the doagent library)
# ---------------------------------------------------------------------------

def create_llm_tool(
    *,
    api_key: Optional[str] = None,
    provider: str = "gemini",
) -> Callable[..., Any]:
    """Create an LLM callable from environment configuration.

    Supported providers:
      - ``"gemini"`` (default): reads ``GEMINI_API_KEY`` or
        ``DOAGENT_GEMINI_API_KEY``.  SDK: ``google-genai``.
      - ``"openai"``: reads ``OPENAI_API_KEY`` or
        ``DOAGENT_OPENAI_API_KEY``.  SDK: ``openai``.

    Returns a callable with signature ``(*, model, messages) -> str``
    that proxies to the provider SDK.  *messages* follows the OpenAI
    chat format (list of ``{"role": ..., "content": ...}`` dicts); the
    Gemini adapter converts internally.

    Raises *RuntimeError* when the API key is missing or the SDK is not
    installed.
    """
    if provider == "gemini":
        key = (
            api_key
            or os.environ.get("DOAGENT_GEMINI_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
        )
        if not key:
            raise RuntimeError(
                "No Gemini API key found.  Set the GEMINI_API_KEY (or "
                "DOAGENT_GEMINI_API_KEY) environment variable, or get a free "
                "key at https://aistudio.google.com/apikey"
            )
        try:
            from google import genai  # type: ignore[import-untyped]
            from google.genai import types  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "The google-genai SDK is required for the Gemini provider.  "
                "Install it with:  pip install google-genai"
            ) from exc

        client = genai.Client(api_key=key)

        def _gemini_call(*, model: str, messages: list) -> str:
            system_parts = [m["content"] for m in messages if m["role"] == "system"]
            user_parts = [m["content"] for m in messages if m["role"] != "system"]
            config = types.GenerateContentConfig(
                system_instruction="\n".join(system_parts) if system_parts else None,
            )
            response = client.models.generate_content(
                model=model,
                contents="\n".join(user_parts),
                config=config,
            )
            return response.text or ""

        return _gemini_call

    if provider == "openai":
        key = (
            api_key
            or os.environ.get("DOAGENT_OPENAI_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
        )
        if not key:
            raise RuntimeError(
                "No OpenAI API key found.  Set the OPENAI_API_KEY (or "
                "DOAGENT_OPENAI_API_KEY) environment variable."
            )
        try:
            from openai import OpenAI  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "The OpenAI SDK is required for the openai provider.  "
                "Install it with:  pip install openai"
            ) from exc

        client = OpenAI(api_key=key)

        def _openai_call(*, model: str, messages: list) -> str:
            response = client.chat.completions.create(
                model=model, messages=messages,
            )
            return response.choices[0].message.content or ""

        return _openai_call

    raise ValueError(f"Unsupported LLM provider: {provider!r}")


_SYSTEM_PROMPT = (
    "You are an agent in a multi-agent environment. "
    "Given the current observation, choose the best action. "
    "Respond with a JSON object containing exactly these fields:\n"
    '  "action": <integer action id>,\n'
    '  "confidence": <float 0.0-1.0>,\n'
    '  "reasoning": "<brief explanation of your choice>"\n'
    "If you cannot determine a good action, set action to null and confidence to 0.0."
)


def _build_user_prompt(
    observation: Any,
    action_space: Dict[int, str],
    goal: str,
) -> str:
    actions_desc = "\n".join(f"  {k}: {v}" for k, v in sorted(action_space.items()))
    return (
        f"Goal: {goal}\n\n"
        f"Observation:\n{json.dumps(observation, default=str, indent=2)}\n\n"
        f"Available actions:\n{actions_desc}\n\n"
        "Choose an action and respond with JSON only."
    )


def _parse_llm_output(raw: Any) -> Dict[str, Any]:
    """Extract JSON from an OpenAI-compatible response object or raw string."""
    if isinstance(raw, str):
        text = raw
    elif hasattr(raw, "choices"):
        choice = raw.choices[0]
        msg = getattr(choice, "message", choice)
        text = getattr(msg, "content", None) or str(msg)
    elif isinstance(raw, dict):
        choices = raw.get("choices", [])
        if choices:
            text = choices[0].get("message", {}).get("content", "")
        else:
            text = json.dumps(raw)
    else:
        text = str(raw)

    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    return json.loads(text)


def llm_decide_factory(params: Dict[str, Any]) -> Any:
    """Policy factory: returns a decide callable that uses an LLM tool.

    Params:
        model: Model identifier passed to the LLM callable (default "gemini-2.5-flash").
        action_space: Dict mapping action integers to descriptions.
        confidence_threshold: Below this confidence, the agent abstains (default 0.3).
        system_prompt: Optional override for the system prompt.
        build_prompt: Optional callable ``(observation, action_space, goal) -> str``
            that builds the user message.  When omitted the default prompt
            template is used.
    """
    model = params.get("model", "gemini-2.5-flash")
    action_space: Dict[int, str] = params.get("action_space", {0: "noop"})
    threshold = float(params.get("confidence_threshold", 0.3))
    system_prompt = params.get("system_prompt", _SYSTEM_PROMPT)
    build_prompt: Callable[..., str] = params.get("build_prompt", _build_user_prompt)

    def decide(request: Dict[str, Any]) -> Dict[str, Any]:
        tools = request.get("tools", {})
        llm = tools.get("llm")
        if llm is None:
            return {
                "choice": {
                    "status": "error",
                    "action": None,
                    "error": "No 'llm' tool provided in agent config.",
                },
            }

        obs = request.get("inputs", {}).get("observation", {})
        goal = request.get("goal", "act optimally")
        user_prompt = build_prompt(obs, action_space, goal)

        try:
            raw_response = llm(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            return {
                "choice": {
                    "status": "error",
                    "action": None,
                    "error": f"LLM call failed: {exc}",
                },
            }

        try:
            parsed = _parse_llm_output(raw_response)
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            return {
                "choice": {
                    "status": "error",
                    "action": None,
                    "error": f"Failed to parse LLM output: {exc}",
                },
            }

        action = parsed.get("action")
        confidence = float(parsed.get("confidence", 0.0))
        reasoning_text = parsed.get("reasoning", "")

        if action is None or confidence < threshold:
            return {
                "choice": {"status": "abstain", "action": None},
                "reasoning": {"source": "llm", "text": reasoning_text, "confidence": confidence},
                "explanation": reasoning_text or "Low confidence — abstaining.",
            }

        if isinstance(action, (int, float)):
            action = int(action)

        return {
            "choice": {"status": "act", "action": action},
            "reasoning": {"source": "llm", "text": reasoning_text, "confidence": confidence},
            "explanation": reasoning_text,
        }

    return decide
