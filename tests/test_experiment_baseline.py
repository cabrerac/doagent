"""Tests for shared experiment measurement helpers."""

import unittest
from pathlib import Path
import tempfile

from experiments._shared import output_bytes_from_path


class TestOutputBytesFromPath(unittest.TestCase):
    def test_counts_nested_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "metadata.json").write_text("abcd", encoding="utf-8")
            records = root / "records"
            records.mkdir()
            (records / "agent_update.jsonl").write_text("efghij", encoding="utf-8")

            self.assertEqual(
                output_bytes_from_path(root),
                len("abcd".encode("utf-8")) + len("efghij".encode("utf-8")),
            )

    def test_missing_path_is_zero(self) -> None:
        self.assertEqual(output_bytes_from_path(None), 0)
        self.assertEqual(output_bytes_from_path("does-not-exist"), 0)


if __name__ == "__main__":
    unittest.main()
