"""Generic LLM decision policy for repository examples.

This is example code, not part of the doagent library.
Provider transport lives in ``llm_client``; this module only builds prompts and maps model output onto a Session ``choice``.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict


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
        model: Model identifier passed to the LLM callable (default "gpt-4o").
        action_space: Dict mapping action integers to descriptions.
        confidence_threshold: Below this confidence the agent abstains (default 0.3).
        system_prompt: Optional override for the system prompt.
        build_prompt: Optional callable taking the observation, action space, and goal, and returning the user message.
            When omitted, the default prompt template is used.
    """
    model = params.get("model", "gpt-4o")
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

        inputs = request.get("inputs", {})
        goal = request.get("goal", "act optimally")
        user_prompt = build_prompt(inputs, action_space, goal)

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
