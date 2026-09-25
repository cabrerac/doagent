"""Retries around a failing model call."""

import builtins
import types
import unittest

from datetime import datetime

from experiments.multiagentbench.run_werewolf_service import (
    _install_prompt_paths,
    call_with_retry,
    note_usage,
    posix_path,
    stamp_line,
    timed_call,
    game_directory,
)


class PromptPathTests(unittest.TestCase):
    def test_backslash_prompt_path_uses_forward_slashes(self) -> None:
        path = posix_path(r"marble\agent\werewolf_prompts\seer_prompt.yaml")
        self.assertEqual(path, "marble/agent/werewolf_prompts/seer_prompt.yaml")

    def test_module_without_open_still_rewrites_the_path(self) -> None:
        module = types.ModuleType("agent")
        exec(
            "def reader():\n"
            "    return open(r'marble\\agent\\werewolf_prompts\\seer_prompt.yaml')\n",
            module.__dict__,
        )
        seen = []

        def fake_open(file: str, *args: object, **kwargs: object) -> None:
            seen.append(file)

        original_open = builtins.open
        builtins.open = fake_open
        try:
            _install_prompt_paths(module)
            module.reader()
        finally:
            builtins.open = original_open
        self.assertEqual(seen, ["marble/agent/werewolf_prompts/seer_prompt.yaml"])


class CallRetryTests(unittest.TestCase):
    def test_retries_until_the_call_returns(self) -> None:
        waits = []
        tries = {"count": 0}

        def operation() -> str:
            tries["count"] += 1
            if tries["count"] < 3:
                raise TimeoutError("Request timed out.")
            return "ok"

        result = call_with_retry(
            operation,
            attempts=5,
            pause=waits.append,
            base_delay=20,
        )
        self.assertEqual(result, "ok")
        self.assertEqual(tries["count"], 3)
        self.assertEqual(waits, [20, 40])

    def test_completion_usage_adds_to_the_token_sum(self) -> None:
        sink = {"tokens": 0, "reported": False}
        response = types.SimpleNamespace(usage=types.SimpleNamespace(total_tokens=12))
        note_usage(response, sink)
        note_usage(types.SimpleNamespace(usage=None), sink)
        self.assertEqual(sink["tokens"], 12)
        self.assertTrue(sink["reported"])

    def test_stamped_line_starts_with_the_time(self) -> None:
        text = stamp_line("Night 1 begins", datetime(2026, 9, 25, 1, 55, 1))
        self.assertTrue(text.startswith("01:55:01 "))
        self.assertIn("Night 1 begins", text)

    def test_finished_call_reports_elapsed_seconds(self) -> None:
        ticks = iter([10.0, 12.5])
        value, elapsed = timed_call(lambda: "ok", clock=lambda: next(ticks))
        self.assertEqual(value, "ok")
        self.assertEqual(elapsed, 2.5)

    def test_renamed_folder_is_used_when_the_original_is_gone(self) -> None:
        import tempfile
        from pathlib import Path

        root = Path(tempfile.mkdtemp())
        renamed = root / "game_1_Werewolves_win"
        renamed.mkdir()
        (renamed / "truth.json").write_text("{}", encoding="utf-8")
        stored = root / "game_1" / "shared_memory.json"
        self.assertEqual(game_directory(str(stored)), renamed)

    def test_raises_after_the_last_attempt(self) -> None:
        def operation() -> None:
            raise TimeoutError("Request timed out.")

        with self.assertRaises(TimeoutError):
            call_with_retry(operation, attempts=2, pause=lambda _delay: None, base_delay=1)


if __name__ == "__main__":
    unittest.main()
