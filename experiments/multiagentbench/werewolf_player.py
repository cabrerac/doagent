"""Load a published Werewolf prompt and call the model.

The prompt files stay in the MARBLE checkout.
The user text starts with the name of the player who is being asked.
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
_TASK_DESCRIPTIONS = {
    "protect_seer": "Keep the seer alive by focusing on their safety.",
    "rescue_villager": "Use antidote or supportive actions to save a villager.",
    "run_for_sheriff": "Attempt to become the elected sheriff for additional influence.",
    "exile_werewolf": "Coordinate with others to vote out a suspected werewolf.",
    "poison_werewolf": "Use poison to eliminate a werewolf during the night phase.",
}
_WITCH_TASKS = (
    "protect_seer",
    "rescue_villager",
    "run_for_sheriff",
    "exile_werewolf",
    "poison_werewolf",
)
_OTHER_TASKS = ("protect_seer", "run_for_sheriff", "exile_werewolf")
_COOPERATIVE = (
    "\n\nRemember, you are using a cooperative strategy. "
    "In your decisions, prioritize teamwork and collaboration "
    "with other villagers to increase your chances of success."
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


def fill_prompt(template: str, fields: Mapping[str, str]) -> str:
    """Replace each published placeholder.

    Args:
        template: User prompt text from the published file.
        fields: Placeholder name to the text that replaces it.
            The name is the token inside the angle brackets.

    Returns:
        The user prompt with those placeholders replaced.
    """
    text = template
    for name, value in fields.items():
        text = text.replace(f"<<{name}>>", value)
    return text


def task_suffix(role: str, public_tasks: list, villager: bool) -> str:
    """Return the task block and the villager strategy line.

    Args:
        role: The acting player's role.
        public_tasks: Task names published for this day.
        villager: True for every role except wolf.

    Returns:
        Text appended to the user prompt.
        Empty when there is no task and the player is a wolf.
    """
    allowed = _WITCH_TASKS if role == "witch" else _OTHER_TASKS
    chosen = [name for name in allowed if name in public_tasks]
    parts = []
    if chosen:
        lines = [
            f"{name}: {_TASK_DESCRIPTIONS.get(name, 'No description available.')}"
            for name in chosen
        ]
        parts.append(
            "\n\n=============================[Optional Daily Tasks]=============================\n"
            "Here are the tasks relevant to you:\n"
            + "\n".join(lines)
            + "\nYou may incorporate them if appropriate."
        )
    if villager:
        parts.append(_COOPERATIVE)
    return "".join(parts)


def label_player(user: str, player_id: str) -> str:
    """Prefix the user prompt with the acting player's name.

    Args:
        user: Filled user prompt.
        player_id: Player who is being asked.

    Returns:
        The prompt, starting with who is deciding.
    """
    return f"You are {player_id}.\n\n{user}"


def label_player_messages(messages: list, player_id: str) -> list:
    """Return a copy of the messages with the acting player named.

    Args:
        messages: System and user messages about to be sent.
        player_id: Player who is being asked.

    Returns:
        A new message list.
        The user text starts with who is deciding.
    """
    labeled = []
    for message in messages:
        if isinstance(message, dict) and message.get("role") == "user":
            content = label_player(str(message.get("content", "")), player_id)
            labeled.append({**message, "content": content})
        else:
            labeled.append(message)
    return labeled


def werewolf_policy(
    player_id: str,
    read_lines: Callable[[], str],
    logging_level: int,
    complete: Callable[[list, list], Mapping[str, Any]],
) -> Callable[[Dict[str, Any]], Any]:
    """Build the decision function for one player.

    Args:
        player_id: Player who is being asked.
        read_lines: Returns the session lines addressed to this player.
        logging_level: 0, 1, or 2. Level 2 asks for an explanation.
        complete: Calls the model with messages and tools.
            Returns a mapping with action, and explanation when level is 2.

    Returns:
        A factory that returns the decision function.
        The action name comes from the observation on the request.
    """

    def factory(_params: Dict[str, Any]) -> Any:
        def policy(request: Dict[str, Any]) -> Dict[str, Any]:
            observation = request["inputs"].get("observation") or {}
            action_name = observation.get("action", "werewolf_action")
            prompt = load_prompt(action_name)
            fields = {
                "public_chat": read_lines(),
                "game_state": str(observation.get("game_state", "")),
                "player info": str(observation.get("player_info", "")),
            }
            extra = observation.get("fields") or {}
            if isinstance(extra, dict):
                for name, value in extra.items():
                    fields[str(name)] = str(value)
            user = fill_prompt(prompt["user"], fields)
            role = str(observation.get("role", ""))
            tasks = observation.get("public_tasks") or []
            if not isinstance(tasks, list):
                tasks = []
            user = user + task_suffix(
                role,
                [str(item) for item in tasks],
                role in ("villager", "seer", "witch", "guard"),
            )
            if logging_level >= 2:
                user = f"{user}\n\n{EXPLANATION_INSTRUCTION}"
            user = label_player(user, player_id)
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
