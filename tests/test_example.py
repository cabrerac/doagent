"""Tests for the minimal example."""

import unittest

from examples.minimal_usage import main


class TestExample(unittest.TestCase):
    def test_minimal_usage_runs(self) -> None:
        """Ensure the minimal usage example runs without errors."""
        main()


if __name__ == "__main__":
    unittest.main(verbosity=2)
