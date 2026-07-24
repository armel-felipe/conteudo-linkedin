import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        from content_ops.db import Database

        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "content.db"
        self.db = Database(self.path)
        self.db.initialize()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_initialize_creates_operational_tables(self):
        with sqlite3.connect(self.path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

        self.assertTrue({"posts", "pillars", "research_reports", "ideas"} <= tables)

    def test_upsert_is_idempotent_by_external_id(self):
        self.db.upsert_post("linkedin:1", "A", "published")
        self.db.upsert_post("linkedin:1", "A revisado", "published")

        self.assertEqual(self.db.count_posts(), 1)
        with sqlite3.connect(self.path) as connection:
            title = connection.execute(
                "SELECT title FROM posts WHERE external_id = ?", ("linkedin:1",)
            ).fetchone()[0]
        self.assertEqual(title, "A revisado")

    def test_create_post_accepts_all_declared_statuses(self):
        from content_ops.models import PostStatus

        for status in PostStatus:
            with self.subTest(status=status.value):
                self.db.create_post(status, f"Post {status.value}")

        self.assertEqual(self.db.count_posts(), len(PostStatus))

    def test_draft_cannot_jump_to_scheduled(self):
        from content_ops.models import PostStatus

        post_id = self.db.create_post("draft", "Teste")

        with self.assertRaises(ValueError):
            self.db.transition_post(post_id, PostStatus.SCHEDULED)

    def test_transition_post_accepts_only_declared_transitions(self):
        from content_ops.models import PostStatus

        allowed_transitions = {
            PostStatus.IDEA: (PostStatus.DRAFT, PostStatus.ARCHIVED),
            PostStatus.DRAFT: (PostStatus.IN_REVIEW, PostStatus.ARCHIVED),
            PostStatus.IN_REVIEW: (
                PostStatus.APPROVED,
                PostStatus.REJECTED,
                PostStatus.DRAFT,
            ),
            PostStatus.APPROVED: (PostStatus.SCHEDULED, PostStatus.DRAFT),
            PostStatus.SCHEDULED: (PostStatus.PUBLISHED, PostStatus.FAILED),
            PostStatus.FAILED: (PostStatus.APPROVED, PostStatus.ARCHIVED),
        }

        for source, destinations in allowed_transitions.items():
            for destination in destinations:
                with self.subTest(source=source.value, destination=destination.value):
                    post_id = self.db.create_post(source, "Teste")
                    self.db.transition_post(post_id, destination)

                    with sqlite3.connect(self.path) as connection:
                        status = connection.execute(
                            "SELECT status FROM posts WHERE id = ?", (post_id,)
                        ).fetchone()[0]
                    self.assertEqual(status, destination.value)

    def test_transition_post_rejects_missing_post(self):
        from content_ops.models import PostStatus

        with self.assertRaises(ValueError):
            self.db.transition_post(999, PostStatus.DRAFT)

    def test_transaction_acquires_the_write_lock_before_reading_approval_count(self):
        with patch.object(self.db, "_begin_immediate", wraps=self.db._begin_immediate) as begin:
            with self.db.transaction() as connection:
                self.assertTrue(connection.in_transaction)

        begin.assert_called_once()


if __name__ == "__main__":
    unittest.main()
