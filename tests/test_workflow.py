import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ResearchCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.target_path = Path(self.temporary_directory.name) / "recent.md"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_capture_writes_command_stdout_verbatim(self):
        from content_ops.research import capture_research

        output = "# Evidência\n\nTexto preservado.\n"
        with patch(
            "content_ops.research.subprocess.run",
            return_value=subprocess.CompletedProcess(["last30days"], 0, output, ""),
        ):
            path = capture_research("IA aplicada", "last30days", self.target_path)

        self.assertEqual(path, self.target_path)
        self.assertEqual(self.target_path.read_text(encoding="utf-8"), output)

    def test_capture_failure_does_not_write_a_report(self):
        from content_ops.research import capture_research

        with patch(
            "content_ops.research.subprocess.run",
            return_value=subprocess.CompletedProcess(["last30days"], 1, "partial", "failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "exit code 1"):
                capture_research("IA aplicada", "last30days", self.target_path)

        self.assertFalse(self.target_path.exists())


class EditorialWorkflowTests(unittest.TestCase):
    def setUp(self):
        from content_ops.db import Database

        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.database = Database(self.root / "content.db")
        self.database.initialize()
        self.draft_path = self.root / "draft.md"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_new_draft_is_traceable_and_unapproved(self):
        from content_ops.markdown import read_post_record
        from content_ops.workflow import create_draft

        path = create_draft(
            {"id": "idea-1", "research_path": "research/x.md", "angle": "..."},
            "IA aplicada",
            self.draft_path,
        )
        metadata, _ = read_post_record(path)

        self.assertEqual(metadata["status"], "draft")
        self.assertFalse(metadata["approved"])
        self.assertEqual(metadata["research_path"], "research/x.md")
        self.assertEqual(metadata["pillar"], "IA aplicada")
        self.assertEqual(metadata["objective"], "authority_and_job_opportunities")
        self.assertIsNone(metadata["image_url"])
        self.assertIsNone(metadata["zernio_post_id"])

    def test_idea_creation_rejects_an_unapproved_pillar(self):
        from content_ops.workflow import create_idea

        self.database.upsert_pillar("IA aplicada")
        self.database.create_research_report("IA", "research/ia.md")

        with self.assertRaisesRegex(ValueError, "not approved"):
            create_idea(self.database, "research/ia.md", "IA aplicada", "Ângulo")

    def test_idea_creation_records_only_an_approved_pillar(self):
        from content_ops.workflow import create_idea

        self.database.upsert_pillar("IA aplicada")
        self.database.approve_pillar("IA aplicada")
        self.database.create_research_report("IA", "research/ia.md")

        idea = create_idea(self.database, "research/ia.md", "IA aplicada", "Ângulo")

        self.assertEqual(idea["pillar"], "IA aplicada")
        self.assertEqual(idea["research_path"], "research/ia.md")
        self.assertEqual(idea["angle"], "Ângulo")


if __name__ == "__main__":
    unittest.main()
