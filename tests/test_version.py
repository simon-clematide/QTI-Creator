"""Tests for version management and metadata."""

import re
import unittest
from src import __version__, __release_date__
from src.version import __version__ as ver, __release_date__ as rdate


class TestVersionManagement(unittest.TestCase):

    def test_version_format(self):
        # Version must follow semver v0.X.Y
        self.assertEqual(__version__, ver)
        self.assertTrue(bool(re.match(r"^0\.\d+\.\d+$", __version__)), f"Version '{__version__}' does not match 0.X.Y")

    def test_release_date_format(self):
        # Release date must follow YYYY-MM-DD
        self.assertEqual(__release_date__, rdate)
        self.assertTrue(bool(re.match(r"^\d{4}-\d{2}-\d{2}$", __release_date__)), f"Date '{__release_date__}' is not YYYY-MM-DD")


if __name__ == "__main__":
    unittest.main()
