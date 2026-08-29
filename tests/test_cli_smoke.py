import os
import subprocess
import tempfile
import unittest
import json
from contextlib import redirect_stdout
from io import StringIO
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

    def test_help_lists_workflow_commands(self):
        result = subprocess.run(["./contentctl", "--help"], text=True, capture_output=True)

        self.assertEqual(result.returncode, 0)
        for command in ("workflow-cycle-start", "workflow-review", "workflow-block-complete"):
            self.assertIn(command, result.stdout)

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

    def test_workflow_cli_runs_cycle_review_and_completion_once(self):
        from content_ops.cli import main
        from content_ops.db import Database

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "content" / "drafts" / "x.md"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("draft", encoding="utf-8")
            database = Database(root / "data" / "content.db")
            database.initialize()
            round_id = database.create_round("Pilar", "round.md")
            for block in ("B1", "B2", "B3", "B4"):
                database.record_workflow_event(round_id, block, "block_completed")
            main(["workflow-cycle-start", str(round_id), "B5", "content/drafts/x.md"], repository_root=root)
            result = json.dumps({"decision": "approved", "artifact": "content/drafts/x.md", "feedback": [], "checks": [{"name": "x", "status": "pass", "evidence": "ok"}]})
            main(["workflow-review", str(round_id), "B5", "content/drafts/x.md", "1", "revisor", result], repository_root=root)
            output = StringIO()
            with redirect_stdout(output):
                main(["workflow-block-complete", str(round_id), "B5", "content/drafts/x.md", "1"], repository_root=root)
            self.assertIn("Completed B5", output.getvalue())
            with self.assertRaises(SystemExit):
                main(["workflow-block-complete", str(round_id), "B5", "content/drafts/x.md", "1"], repository_root=root)

    def test_workflow_cli_rejects_b7_and_legacy_bloco_ok(self):
        from content_ops.cli import main
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(SystemExit):
                main(["bloco-ok", "B5", "x.md"], repository_root=root)
            database = __import__("content_ops.db", fromlist=["Database"]).Database(root / "data" / "content.db")
            database.initialize()
            round_id = database.create_round("Pilar", "round.md")
            for block in ("B1", "B2", "B3", "B4", "B5", "B6"):
                database.record_workflow_event(round_id, block, "block_completed")
            artifact = root / "artifact.md"
            artifact.write_text("draft", encoding="utf-8")
            main(["workflow-cycle-start", str(round_id), "B7", "artifact.md"], repository_root=root)
            result = json.dumps({"decision": "approved", "artifact": "artifact.md", "feedback": [], "checks": [{"name": "x", "status": "pass", "evidence": "ok"}]})
            with self.assertRaises(SystemExit):
                main(["workflow-review", str(round_id), "B7", "artifact.md", "1", "revisor", result], repository_root=root)

    def test_workflow_cli_persists_human_b7_completion(self):
        from content_ops.cli import main
        from content_ops.db import Database
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "artifact.md"
            artifact.write_text("draft", encoding="utf-8")
            database = Database(root / "data" / "content.db")
            database.initialize()
            round_id = database.create_round("Pilar", "round.md")
            for block in ("B1", "B2", "B3", "B4", "B5", "B6"):
                database.record_workflow_event(round_id, block, "block_completed")
            main(["workflow-human-complete", str(round_id), "B7", "artifact.md", "idea-1"], repository_root=root)
            self.assertEqual(database.latest_block_state(round_id, "B7")["event"], "human_completed")
