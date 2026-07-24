import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class CliSmokeTests(unittest.TestCase):
    def test_required_operational_directories_have_gitkeep_files(self):
        repository_root = Path(__file__).resolve().parents[1]
        required_directories = (
            "research",
            "content/ideas",
            "content/drafts",
            "content/approved",
            "content/published",
            "calendar",
            "data/imports",
            "docs",
        )

        for directory in required_directories:
            with self.subTest(directory=directory):
                self.assertTrue((repository_root / directory / ".gitkeep").is_file())

    def test_help_lists_history(self):
        result = subprocess.run(["./contentctl", "--help"], text=True, capture_output=True)

        self.assertEqual(result.returncode, 0)
        self.assertIn("history", result.stdout)

    def test_load_env_sets_missing_values_without_overriding_existing_ones(self):
        from content_ops.cli import load_env

        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / ".env"
            env_file.write_text(
                "# Local configuration\nFROM_FILE=loaded\nEXISTING=from-file\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"EXISTING": "from-environment"}, clear=True):
                load_env(env_file)

                self.assertEqual(os.environ["FROM_FILE"], "loaded")
                self.assertEqual(os.environ["EXISTING"], "from-environment")
