"""Measure Werewolf storage and tokens from a finished repetition.

Levels 0 and 1 are the level 2 records with the extra fields removed.
Their token totals drop the explanation sentence and the explanation text.
The service size is the player logs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from experiments.attribution.projections import project_logging_level
from experiments.multiagentbench.werewolf_player import EXPLANATION_INSTRUCTION

RECORD_NAMES = ("agent_update.jsonl", "outcome.jsonl", "trace.jsonl")
RECORD_KINDS = frozenset(name[: -len(".jsonl")] for name in RECORD_NAMES)
EXPLANATION_SUFFIX = "\n\n" + EXPLANATION_INSTRUCTION
_encoder: Any = None


def cl100k_encode(text: str) -> list[int]:
    """Encode text with the cl100k tokenizer.

    Args:
        text: Prompt or reply text.

    Returns:
        Token ids for that text.
    """
    global _encoder
    if _encoder is None:
        import tiktoken

        _encoder = tiktoken.get_encoding("cl100k_base")
    return list(_encoder.encode(text))


def user_text(messages: Sequence[Mapping[str, Any]]) -> str:
    """Return the user message from one model request.

    Args:
        messages: System and user messages sent to the model.

    Returns:
        The user text.
        An empty string when no user message is present.
    """
    for message in messages:
        if message.get("role") == "user":
            return str(message.get("content") or "")
    return ""


def explanation_overhead(
    user: str,
    explanation: Any,
    encode: Callable[[str], Sequence[int]],
) -> int:
    """Return the explanation tokens in one request and its reply.

    Args:
        user: User message sent to the model.
        explanation: Explanation text from the reply.
        encode: Turns text into token ids.

    Returns:
        Tokens added by the explanation sentence, plus tokens in the explanation text.
        Zero for the sentence when the user message does not end with it.
    """
    request = 0
    if user.endswith(EXPLANATION_SUFFIX):
        request = len(encode(user)) - len(encode(user[: -len(EXPLANATION_SUFFIX)]))
    reply = 0
    if isinstance(explanation, str) and explanation:
        reply = len(encode(explanation))
    return request + reply


def overhead_from_records(
    records: Sequence[Mapping[str, Any]],
    encode: Callable[[str], Sequence[int]],
) -> int:
    """Return the explanation tokens stored for a level 2 session.

    The sentence is encoded on its own, once per agent update.
    The reply text is the explanation on that update.

    Args:
        records: Native records from a level 2 session.
        encode: Turns text into token ids.

    Returns:
        The token count to subtract from the level 2 total.
    """
    sentence = len(encode(EXPLANATION_SUFFIX))
    total = 0
    calls = 0
    for record in records:
        if record.get("kind") != "agent_update":
            continue
        calls += 1
        decision = (record.get("payload") or {}).get("decision") or {}
        if not isinstance(decision, dict):
            continue
        response = decision.get("response") or {}
        text = response.get("explanation") if isinstance(response, dict) else ""
        if isinstance(text, str) and text:
            total += len(encode(text))
    return total + calls * sentence


def token_levels(tokens: int, overhead: int) -> dict[str, int]:
    """Return level 0, 1, and 2 token totals for a level 2 game.

    Args:
        tokens: Proxy total for the level 2 game.
        overhead: Tokens in the explanation sentence and the explanation text.

    Returns:
        The three totals.
        Levels 0 and 1 share the total with the explanation tokens removed.
    """
    reduced = tokens - overhead
    if reduced < 0:
        reduced = 0
    return {"0": reduced, "1": reduced, "2": tokens}


def write_cost(
    directory: Path,
    wall_seconds: float,
    tokens: Optional[int],
    sources: Sequence[Path],
    tokens_by_level: Optional[Mapping[str, int]] = None,
) -> None:
    """Write tokens, wall time, and the size of the given record files.

    Args:
        directory: Directory that receives cost.json.
        wall_seconds: Seconds spent playing the game.
        tokens: Total model tokens for the run.
            None when the model call did not report usage.
        sources: Record files to measure.
            A path that is not a file is left out.
        tokens_by_level: Token totals for logging levels 0, 1, and 2.
            Omitted when the run has no split.
    """
    files = [path for path in sources if path.is_file()]
    payload: dict[str, Any] = {
        "storage_bytes": sum(path.stat().st_size for path in files),
        "file_count": len(files),
        "tokens": tokens,
        "wall_seconds": wall_seconds,
    }
    if tokens_by_level is not None:
        payload["tokens_by_level"] = {
            str(level): int(tokens_by_level[str(level)]) for level in ("0", "1", "2")
        }
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "cost.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def doagent_record_paths(run_path: Path) -> list[Path]:
    """Return the three DOAgent record files for one session.

    Args:
        run_path: Session directory that contains the records folder.

    Returns:
        Paths of the agent update, outcome, and trace files.
        A missing file is still listed.
    """
    records = Path(run_path) / "records"
    return [records / name for name in RECORD_NAMES]


def service_log_paths(directory: Path) -> list[Path]:
    """Return the player logs in one service game directory.

    Args:
        directory: Folder that holds the per-player logs.

    Returns:
        The log files, sorted by name.
    """
    return sorted(Path(directory).glob("*_log.txt"))


def load_records(records_dir: Path) -> list[dict[str, Any]]:
    """Read the DOAgent record files in one session.

    Args:
        records_dir: Folder that holds the JSONL record files.

    Returns:
        Every record from the files that exist.
    """
    records: list[dict[str, Any]] = []
    for name in RECORD_NAMES:
        path = Path(records_dir) / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    return records


def projected_storage(records: Sequence[Mapping[str, Any]], level: int) -> dict[str, int]:
    """Return the storage a run at this logging level would keep.

    Args:
        records: Native records from a level 2 session.
        level: Logging level, 0, 1, or 2.

    Returns:
        storage_bytes and file_count for the record files at that level.
    """
    by_kind: dict[str, list[Mapping[str, Any]]] = {}
    for record in project_logging_level(records, level):
        kind = record.get("kind")
        if kind not in RECORD_KINDS:
            continue
        by_kind.setdefault(str(kind), []).append(record)
    storage = 0
    for items in by_kind.values():
        for item in items:
            encoded = json.dumps(item, sort_keys=True) + "\n"
            storage += len(encoded.encode("utf-8"))
    return {"storage_bytes": storage, "file_count": len(by_kind)}


def _played_cost(path: Path) -> dict[str, Any]:
    """Return tokens and wall time from a cost file written during a game.

    Args:
        path: cost.json from one arm.

    Returns:
        tokens, wall_seconds, and tokens_by_level.
        None for each field when the file or the field is missing.
    """
    if not path.is_file():
        return {"tokens": None, "wall_seconds": None, "tokens_by_level": None}
    document = json.loads(path.read_text(encoding="utf-8"))
    levels = document.get("tokens_by_level")
    if not isinstance(levels, dict):
        levels = None
    return {
        "tokens": document.get("tokens"),
        "wall_seconds": document.get("wall_seconds"),
        "tokens_by_level": levels,
    }


def _has_level2_explanation(records: Sequence[Mapping[str, Any]]) -> bool:
    """Return whether the session stored level 2 explanations.

    Args:
        records: Native records from one session.

    Returns:
        True when an agent update carries an explanation field.
    """
    for record in records:
        if record.get("kind") != "agent_update":
            continue
        decision = (record.get("payload") or {}).get("decision") or {}
        if isinstance(decision, dict) and "explanation" in decision:
            return True
    return False


def projected_tokens(
    tokens: Optional[int],
    records: Sequence[Mapping[str, Any]],
    tokens_by_level: Optional[Mapping[str, Any]],
    encode: Callable[[str], Sequence[int]],
) -> dict[str, Optional[int]]:
    """Return token totals for logging levels 0, 1, and 2.

    A stored split is kept.
    A level 2 session without that split subtracts the explanation sentence and the explanation text.

    Args:
        tokens: Proxy total for the game that ran.
        records: Native records from that game.
        tokens_by_level: Split stored by the runner.
            None when the cost file has no split.
        encode: Turns text into token ids.

    Returns:
        One total for each logging level.
        None when the proxy total is missing.
    """
    if isinstance(tokens_by_level, dict) and all(
        str(level) in tokens_by_level for level in (0, 1, 2)
    ):
        return {str(level): int(tokens_by_level[str(level)]) for level in (0, 1, 2)}
    if tokens is None:
        return {str(level): None for level in (0, 1, 2)}
    if _has_level2_explanation(records):
        return token_levels(int(tokens), overhead_from_records(records, encode))
    return {str(level): tokens for level in (0, 1, 2)}


def _records_dir(doagent_dir: Path) -> Optional[Path]:
    """Return the records folder of the session under a DOAgent game directory.

    Args:
        doagent_dir: Folder that contains the session directory.

    Returns:
        The records folder.
        None when no session is present.
    """
    matches = sorted(Path(doagent_dir).glob("werewolf_doagent_run_*/records"))
    if len(matches) != 1:
        return None
    return matches[0]


def _service_game_dir(service_dir: Path) -> Optional[Path]:
    """Return the game folder that holds the player logs.

    Args:
        service_dir: Folder passed to the service runner.

    Returns:
        The game folder.
        None when no player log is present.
    """
    parents = {path.parent for path in Path(service_dir).glob("game_*/*_log.txt")}
    if len(parents) != 1:
        return None
    return parents.pop()


def summarize_repetition(
    repetition: Path,
    encode: Optional[Callable[[str], Sequence[int]]] = None,
) -> dict[str, Any]:
    """Return DOAgent levels 0, 1, and 2, and the service logs, for one pair.

    Args:
        repetition: Folder with doagent/ and service/ from one repetition.
        encode: Turns text into token ids.
            The cl100k tokenizer is used when this is omitted.

    Returns:
        Storage for each DOAgent level and for the service logs.
        Level 2 tokens are the proxy total.
        Levels 0 and 1 omit the explanation sentence and the explanation text.
        Wall time is the clock of the game that ran.
    """
    repetition = Path(repetition)
    records_dir = _records_dir(repetition / "doagent")
    records = load_records(records_dir) if records_dir is not None else []
    played = _played_cost(repetition / "doagent" / "cost.json")
    encoder = encode if encode is not None else cl100k_encode
    totals = projected_tokens(
        played["tokens"],
        records,
        played["tokens_by_level"],
        encoder,
    )
    doagent = {}
    for level in (0, 1, 2):
        measured = projected_storage(records, level)
        measured["tokens"] = totals[str(level)]
        measured["wall_seconds"] = played["wall_seconds"]
        doagent[str(level)] = measured
    game_dir = _service_game_dir(repetition / "service")
    logs = service_log_paths(game_dir) if game_dir is not None else []
    service_played = _played_cost(game_dir / "cost.json") if game_dir is not None else {
        "tokens": None,
        "wall_seconds": None,
    }
    service = {
        "storage_bytes": sum(path.stat().st_size for path in logs),
        "file_count": len(logs),
        "tokens": service_played["tokens"],
        "wall_seconds": service_played["wall_seconds"],
    }
    return {"doagent": doagent, "service": service}


def main(argv: list[str] | None = None) -> None:
    """Write cost_summary.json for one finished repetition."""
    parser = argparse.ArgumentParser(description="Werewolf cost from a finished repetition")
    parser.add_argument("repetition", type=Path)
    args = parser.parse_args(argv)
    summary = summarize_repetition(args.repetition)
    text = json.dumps(summary, indent=2)
    (args.repetition / "cost_summary.json").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
