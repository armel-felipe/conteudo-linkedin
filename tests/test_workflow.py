import json
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

        output = b"# Evid\xc3\xaancia\n\nTexto preservado.\n\xff\x00"
        with patch(
            "content_ops.research.subprocess.run",
            return_value=subprocess.CompletedProcess(["last30days"], 0, output, ""),
        ) as run:
            path = capture_research("IA aplicada", "last30days", self.target_path)

        self.assertEqual(path, self.target_path)
        self.assertEqual(self.target_path.read_bytes(), output)
        self.assertFalse(run.call_args.kwargs["text"])

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
        from content_ops.workflow import create_draft, create_idea

        self.database.upsert_pillar("IA aplicada")
        self.database.approve_pillar("IA aplicada")
        self.database.create_research_report("IA", "research/x.md")
        idea = create_idea(self.database, "research/x.md", "IA aplicada", "...")
        path = create_draft(
            self.database,
            idea,
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
        self.assertIsNone(metadata["suggested_time"])
        self.assertEqual(
            metadata["sources"],
            [{"type": "research", "path": "research/x.md"}],
        )
        self.assertIsNone(metadata["published_url"])
        self.assertEqual(metadata["metrics"], {})
        self.assertIsNone(metadata["publication_result"])
        with self.database._connect() as connection:
            stored = connection.execute(
                "SELECT suggested_time, sources FROM posts WHERE id = ?",
                (metadata["post_id"],),
            ).fetchone()
        self.assertIsNone(stored["suggested_time"])
        self.assertEqual(
            json.loads(stored["sources"]),
            [{"path": "research/x.md", "type": "research"}],
        )

    def test_idea_and_draft_creation_are_idempotent(self):
        from content_ops.markdown import read_post_record, write_post_record
        from content_ops.workflow import create_draft, create_idea

        self.database.upsert_pillar("IA aplicada")
        self.database.approve_pillar("IA aplicada")
        self.database.create_research_report("IA", "research/x.md")
        ideas_directory = self.root / "ideas"

        first = create_idea(
            self.database,
            "research/x.md",
            "IA aplicada",
            "Mesmo ângulo",
            ideas_directory=ideas_directory,
        )
        second = create_idea(
            self.database,
            "research/x.md",
            "IA aplicada",
            "Mesmo ângulo",
            ideas_directory=ideas_directory,
        )
        self.assertEqual(first["id"], second["id"])
        with self.database._connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM ideas").fetchone()[0], 1)

        draft = create_draft(self.database, first, "IA aplicada", self.draft_path)
        metadata, _ = read_post_record(draft)
        write_post_record(draft, metadata, "Edição humana preservada")
        create_draft(self.database, second, "IA aplicada", self.draft_path)

        self.assertEqual(read_post_record(draft)[1], "Edição humana preservada")
        with self.database._connect() as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM posts WHERE status = 'draft'").fetchone()[0],
                1,
            )

    def test_idea_markdown_failure_rolls_back_database(self):
        from content_ops.workflow import create_idea

        self.database.upsert_pillar("IA aplicada")
        self.database.approve_pillar("IA aplicada")
        self.database.create_research_report("IA", "research/x.md")

        with patch(
            "content_ops.workflow.write_post_record", side_effect=OSError("disk full")
        ):
            with self.assertRaises(OSError):
                create_idea(
                    self.database,
                    "research/x.md",
                    "IA aplicada",
                    "Ângulo",
                    ideas_directory=self.root / "ideas",
                )

        with self.database._connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM ideas").fetchone()[0], 0)

    def test_idea_post_replace_failure_removes_published_orphan(self):
        from content_ops.markdown import write_post_record
        from content_ops.workflow import create_idea

        self.database.upsert_pillar("IA aplicada")
        self.database.approve_pillar("IA aplicada")
        self.database.create_research_report("IA", "research/x.md")
        ideas_directory = self.root / "ideas"

        def publish_then_fail(path, metadata, body):
            write_post_record(path, metadata, body)
            raise OSError("directory fsync failed")

        with patch(
            "content_ops.workflow.write_post_record",
            side_effect=publish_then_fail,
        ):
            with self.assertRaises(OSError):
                create_idea(
                    self.database,
                    "research/x.md",
                    "IA aplicada",
                    "Ângulo",
                    ideas_directory=ideas_directory,
                )

        self.assertEqual(list(ideas_directory.glob("*.md")), [])
        with self.database._connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM ideas").fetchone()[0], 0)

    def test_draft_markdown_failure_rolls_back_database(self):
        from content_ops.workflow import create_draft, create_idea

        self.database.upsert_pillar("IA aplicada")
        self.database.approve_pillar("IA aplicada")
        self.database.create_research_report("IA", "research/x.md")
        idea = create_idea(self.database, "research/x.md", "IA aplicada", "Ângulo")

        with patch(
            "content_ops.workflow.write_post_record", side_effect=OSError("disk full")
        ):
            with self.assertRaises(OSError):
                create_draft(self.database, idea, "IA aplicada", self.draft_path)

        with self.database._connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM posts").fetchone()[0], 0)
            self.assertIsNone(
                connection.execute(
                    "SELECT draft_post_id FROM ideas WHERE id = ?", (idea["id"],)
                ).fetchone()[0]
            )

    def test_draft_post_replace_failure_removes_published_orphan(self):
        from content_ops.markdown import write_post_record
        from content_ops.workflow import create_draft, create_idea

        self.database.upsert_pillar("IA aplicada")
        self.database.approve_pillar("IA aplicada")
        self.database.create_research_report("IA", "research/x.md")
        idea = create_idea(self.database, "research/x.md", "IA aplicada", "Ângulo")

        def publish_then_fail(path, metadata, body):
            write_post_record(path, metadata, body)
            raise OSError("directory fsync failed")

        with patch(
            "content_ops.workflow.write_post_record",
            side_effect=publish_then_fail,
        ):
            with self.assertRaises(OSError):
                create_draft(self.database, idea, "IA aplicada", self.draft_path)

        self.assertFalse(self.draft_path.exists())
        with self.database._connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM posts").fetchone()[0], 0)

    def test_submit_for_review_rolls_back_database_when_markdown_write_fails(self):
        from content_ops.markdown import read_post_record, write_post_record
        from content_ops.workflow import submit_draft_for_review

        post_id = self.database.create_post("draft", "Rascunho")
        write_post_record(
            self.draft_path,
            {"post_id": post_id, "status": "draft", "approved": False},
            "Texto",
        )

        with patch(
            "content_ops.workflow.write_post_record", side_effect=OSError("disk full")
        ):
            with self.assertRaises(OSError):
                submit_draft_for_review(
                    post_id, self.draft_path, database=self.database
                )

        self.assertEqual(read_post_record(self.draft_path)[0]["status"], "draft")
        with self.database._connect() as connection:
            status = connection.execute(
                "SELECT status FROM posts WHERE id = ?", (post_id,)
            ).fetchone()[0]
        self.assertEqual(status, "draft")

    def test_workflow_rejects_draft_with_a_pillar_different_from_its_idea(self):
        from content_ops.workflow import create_draft, create_idea

        self.database.upsert_pillar("IA aplicada")
        self.database.upsert_pillar("Python e dados")
        self.database.approve_pillar("IA aplicada")
        self.database.approve_pillar("Python e dados")
        self.database.create_research_report("IA", "research/ia.md")
        idea = create_idea(self.database, "research/ia.md", "IA aplicada", "Ângulo")

        with self.assertRaisesRegex(ValueError, "does not match"):
            create_draft(self.database, idea, "Python e dados", self.draft_path)

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

    def test_database_rejects_direct_idea_creation_with_an_unapproved_pillar(self):
        self.database.upsert_pillar("IA aplicada")
        self.database.create_research_report("IA", "research/ia.md")

        with self.assertRaisesRegex(ValueError, "not approved"):
            self.database.create_idea("Ângulo", "IA aplicada", "research/ia.md")

    def test_database_rejects_direct_draft_creation_with_a_different_pillar(self):
        from content_ops.workflow import create_idea

        self.database.upsert_pillar("IA aplicada")
        self.database.upsert_pillar("Python e dados")
        self.database.approve_pillar("IA aplicada")
        self.database.approve_pillar("Python e dados")
        self.database.create_research_report("IA", "research/ia.md")
        idea = create_idea(self.database, "research/ia.md", "IA aplicada", "Ângulo")

        with self.assertRaisesRegex(ValueError, "does not match"):
            self.database.create_draft_for_idea(int(idea["id"]), "Python e dados")


if __name__ == "__main__":
    unittest.main()
