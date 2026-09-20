"""Tests for loading KEY=VALUE pairs from a .env file."""

import os
import tempfile
import unittest
from pathlib import Path

from examples._shared.env_file import load_dotenv


class TestLoadDotenv(unittest.TestCase):
    def _write_env(self, text: str) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / ".env"
        path.write_text(text, encoding="utf-8")
        return path

    def _track_key(self, name: str) -> None:
        self.addCleanup(lambda: os.environ.pop(name, None))

    def test_values_load_into_environment(self):
        key = "DOAGENT_TEST_ENV_KEY"
        self._track_key(key)
        os.environ.pop(key, None)
        path = self._write_env(f"{key}=from-file\n")
        load_dotenv(path)
        self.assertEqual(os.environ[key], "from-file")

    def test_existing_environment_variable_is_not_overwritten(self):
        key = "DOAGENT_TEST_ENV_KEY"
        self._track_key(key)
        os.environ[key] = "from-shell"
        path = self._write_env(f"{key}=from-file\n")
        load_dotenv(path)
        self.assertEqual(os.environ[key], "from-shell")

    def test_comments_and_quoted_values_parse(self):
        keys = (
            "DOAGENT_TEST_ENV_PLAIN",
            "DOAGENT_TEST_ENV_DOUBLE",
            "DOAGENT_TEST_ENV_SINGLE",
            "DOAGENT_TEST_ENV_EXPORT",
        )
        for key in keys:
            self._track_key(key)
            os.environ.pop(key, None)
        path = self._write_env(
            "\n".join(
                [
                    "# comment",
                    "",
                    f"{keys[0]}=plain",
                    f'{keys[1]}="quoted value"',
                    f"{keys[2]}='single'",
                    f"export {keys[3]}=exported",
                ]
            )
            + "\n"
        )
        load_dotenv(path)
        self.assertEqual(os.environ[keys[0]], "plain")
        self.assertEqual(os.environ[keys[1]], "quoted value")
        self.assertEqual(os.environ[keys[2]], "single")
        self.assertEqual(os.environ[keys[3]], "exported")

    def test_missing_file_does_nothing(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        missing = Path(tmp.name) / "no-such.env"
        load_dotenv(missing)
