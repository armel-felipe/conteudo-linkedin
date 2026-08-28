import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


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

    def test_posts_sync_reports_failed_when_remote_post_failed(self):
        from content_ops.markdown import write_post_record
        from content_ops.models import PostStatus

        post_id = self.database.create_post(PostStatus.APPROVED, "Scheduled post")
        self.database.persist_schedule_intent(
            post_id,
            "123e4567-e89b-12d3-a456-426614174000",
            "2030-01-01T10:00:00-03:00",
            {"content": "Scheduled post"},
        )
        self.database.record_schedule_result(post_id, PostStatus.SCHEDULED, "z-1")
        path = self.root / "content" / "drafts" / "scheduled.md"
        write_post_record(
            path, {"post_id": post_id, "status": "scheduled"}, "Scheduled post"
        )

        class FailedPostClient:
            def __init__(self, api_key):
                self.api_key = api_key

            def get_post(self, zernio_post_id):
                return {"status": "FAILED"}

        with (
            patch.dict("content_ops.cli.os.environ", {"ZERNIO_API_KEY": "test-key"}),
            patch("content_ops.zernio.ZernioClient", FailedPostClient),
        ):
            output = self.run_cli(["posts", "sync", str(post_id)])

        self.assertEqual(output, f"Post {post_id} failed.\n")

    def test_research_discover_records_optional_pillar(self):
        from content_ops.research import capture_research

        with (
            patch.dict(
                "content_ops.cli.os.environ",
                {"LAST30DAYS_COMMAND": "echo research-output"},
            ),
            patch.object(capture_research, "__wrapped__", None, create=True),
        ):
            output = self.run_cli(
                [
                    "research",
                    "discover",
                    "liderança em times",
                    "--pillar",
                    "Liderança e gestão de times",
                ]
            )

        self.assertIn("Captured research in", output)
        with self.database._connect() as connection:
            row = connection.execute(
                "SELECT pillar FROM research_reports WHERE topic = ?",
                ("liderança em times",),
            ).fetchone()
        self.assertEqual(row[0], "Liderança e gestão de times")

    def test_pillars_propose_uses_captured_research(self):
        self.database.create_research_report(
            "liderança em times de alta performance",
            "research/lideranca-times.md",
            pillar="Liderança e gestão de times",
        )
        self.database.create_research_report(
            "problem solving metodologia mckinsey",
            "research/problem-solving.md",
            pillar="Liderança e gestão de times",
        )

        output = self.run_cli(["pillars", "propose"])

        self.assertIn("Proposed 2 pillars", output)
        document = (self.root / "docs" / "pillars.md").read_text(encoding="utf-8")
        self.assertIn("## Liderança e gestão de times", document)
        self.assertIn("evidence_ids: research/lideranca-times.md, research/problem-solving.md", document)


if __name__ == "__main__":
    unittest.main()
