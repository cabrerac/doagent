"""Load a published Werewolf prompt and call the model.

The prompt files stay in the MARBLE checkout.
At logging level 2 the player adds an explanation instruction beside that text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Mapping

import yaml

PROMPT_DIR = (
    Path(__file__).resolve().parent
    / "MARBLE"
    / "marble"
    / "agent"
    / "werewolf_prompts"
)
PROMPT_FILES = {
    "werewolf_action": "werewolf_action.yaml",
    "werewolf_discussion": "werewolf_discussion.yaml",
    "guard_action": "guard_prompt.yaml",
    "seer_action": "seer_prompt.yaml",
    "witch_action": "witch_prompt.yaml",
    "run_for_sheriff": "run_for_sheriff.yaml",
    "sheriff_speech": "sheriff_speech.yaml",
    "vote_for_sheriff": "vote_for_sheriff.yaml",
    "last_words": "last_word_prompt.yaml",
    "decide_speech_sequence": "decide_speech_sequence.yaml",
    "player_speech": "speech_prompt.yaml",
    "vote_action": "vote_prompt.yaml",
    "badge_flow": "badge_flow.yaml",
}
EXPLANATION_INSTRUCTION = (
    "Also give a short explanation of this decision. "
    "Put that explanation only in the explanation field."
)


def load_prompt(action_name: str) -> Dict[str, Any]:
    """Load one published prompt file.

    Args:
        action_name: Action key, such as werewolf_action.

    Returns:
        The system text, the user text, and the tool list.

    Raises:
        KeyError: If action_name has no prompt file.
    """
    filename = PROMPT_FILES[action_name]
    with (PROMPT_DIR / filename).open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    return {
        "system": document.get("system", ""),
        "user": document.get("user", ""),
        "tools": document.get("tools", []),
    }


def fill_prompt(template: str, history: str, game_state: str, player_info: str) -> str:
    """Fill the published placeholders.

    Args:
        template: User prompt text from the published file.
        history: Lines this player is allowed to read.
        game_state: Current day, phase, and living players.
        player_info: Facts this action's prompt asks for.

    Returns:
        The user prompt with placeholders replaced.
    """
    text = template.replace("<<public_chat>>", history)
    text = text.replace("<<game_state>>", game_state)
    text = text.replace("<<player info>>", player_info)
    return text


def werewolf_policy(
    player_id: str,
    read_lines: Callable[[], str],
    logging_level: int,
    complete: Callable[[list, list], Mapping[str, Any]],
) -> Callable[[Dict[str, Any]], Any]:
    """Build the decision function for one player.

    Args:
        player_id: Player id. Present so the caller can tell policies apart.
        read_lines: Returns the session lines addressed to this player.
        logging_level: 0, 1, or 2. Level 2 asks for an explanation.
        complete: Calls the model with messages and tools.
            Returns a mapping with action, and explanation when level is 2.

    Returns:
        A factory that returns the decision function.
        The action name comes from the observation on the request.
    """
    del player_id

    def factory(_params: Dict[str, Any]) -> Any:
        def policy(request: Dict[str, Any]) -> Dict[str, Any]:
            observation = request["inputs"].get("observation") or {}
            action_name = observation.get("action", "werewolf_action")
            prompt = load_prompt(action_name)
            user = fill_prompt(prompt["user"], read_lines(), "", "")
            if logging_level >= 2:
                user = f"{user}\n\n{EXPLANATION_INSTRUCTION}"
            messages = [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": user},
            ]
            raw = complete(messages, prompt["tools"])
            response: Dict[str, Any] = {
                "choice": {"status": "act", "action": raw.get("action", {})},
            }
            explanation = raw.get("explanation")
            if logging_level >= 2 and isinstance(explanation, str):
                response["explanation"] = explanation
            return response

        return policy

    return factory
