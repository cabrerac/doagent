"""Retries around a failing model call."""

import unittest

from experiments.multiagentbench.run_werewolf_service import (
    call_with_retry,
    posix_path,
)


class PromptPathTests(unittest.TestCase):
    def test_backslash_prompt_path_uses_forward_slashes(self) -> None:
        path = posix_path(r"marble\agent\werewolf_prompts\seer_prompt.yaml")
        self.assertEqual(path, "marble/agent/werewolf_prompts/seer_prompt.yaml")


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

    def test_raises_after_the_last_attempt(self) -> None:
        def operation() -> None:
            raise TimeoutError("Request timed out.")

        with self.assertRaises(TimeoutError):
            call_with_retry(operation, attempts=2, pause=lambda _delay: None, base_delay=1)


if __name__ == "__main__":
    unittest.main()
