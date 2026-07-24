import contextlib
import io
import tempfile
import unittest
from pathlib import Path


class EditorialCliEndToEndTests(unittest.TestCase):
    def setUp(self):
        from content_ops.db import Database

        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.database = Database(self.root / "data" / "content.db")
        self.database.initialize()
        self.database.upsert_pillar("IA aplicada")
        self.database.approve_pillar("IA aplicada")
        self.database.create_research_report("IA", "research/ia.md")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def run_cli(self, arguments):
        from content_ops.cli import main

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main(arguments, repository_root=self.root)
        return output.getvalue()

    def test_ideas_and_draft_create_dispatch_end_to_end(self):
        from content_ops.markdown import read_post_record

        output = self.run_cli(
            [
                "ideas",
                "create",
                "--research",
                "research/ia.md",
                "--pillar",
                "IA aplicada",
                "--angle",
                "Ângulo verificável",
            ]
        )
        self.assertIn("Created idea 1.", output)
        self.assertTrue((self.root / "content" / "ideas" / "idea-1.md").is_file())

        output = self.run_cli(["draft", "create", "1"])
        self.assertIn("post 1", output)
        metadata, body = read_post_record(
            self.root / "content" / "drafts" / "idea-1.md"
        )
        self.assertEqual(metadata["post_id"], 1)
        self.assertEqual(metadata["status"], "draft")
        self.assertEqual(body, "Ângulo: Ângulo verificável")

    def test_created_draft_can_be_submitted_and_approved_end_to_end(self):
        from content_ops.markdown import read_post_record

        self.run_cli(
            [
                "ideas",
                "create",
                "--research",
                "research/ia.md",
                "--pillar",
                "IA aplicada",
                "--angle",
                "Do rascunho à revisão",
            ]
        )
        self.run_cli(["draft", "create", "1"])

        self.assertIn("Submitted post 1 for review.", self.run_cli(["review", "submit", "1"]))
        path = self.root / "content" / "drafts" / "idea-1.md"
        metadata, _ = read_post_record(path)
        self.assertEqual(metadata["status"], "in_review")
        self.assertFalse(metadata["approved"])

        self.assertIn("Approved post 1.", self.run_cli(["review", "approve", "1"]))
        metadata, _ = read_post_record(path)
        self.assertEqual(metadata["status"], "approved")
        self.assertTrue(metadata["approved"])
        with self.database._connect() as connection:
            status = connection.execute(
                "SELECT status FROM posts WHERE id = 1"
            ).fetchone()[0]
        self.assertEqual(status, "approved")


if __name__ == "__main__":
    unittest.main()
