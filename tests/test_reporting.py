import tempfile
import unittest
from datetime import date
from pathlib import Path


class ReportingTests(unittest.TestCase):
    def setUp(self):
        from content_ops.db import Database
        from content_ops.models import PostStatus

        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temporary_directory.name) / "content.db")
        self.database.initialize()
        self.scheduled = self.database.create_post(PostStatus.APPROVED, "Scheduled post")
        self.database.persist_schedule_intent(
            self.scheduled, "123e4567-e89b-12d3-a456-426614174000",
            "2026-07-28T10:00:00-03:00", {"content": "Scheduled post"},
        )
        self.database.record_schedule_result(self.scheduled, PostStatus.SCHEDULED, "z-1")
        self.published = self.database.create_post(PostStatus.APPROVED, "Published post")
        self.database.persist_schedule_intent(
            self.published, "123e4567-e89b-12d3-a456-426614174001",
            "2026-08-02T10:00:00-03:00", {"content": "Published post"},
        )
        self.database.record_schedule_result(self.published, PostStatus.SCHEDULED, "z-2")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_weekly_report_counts_cadence(self):
        from content_ops.reporting import weekly_report

        report = weekly_report(self.database, date(2026, 7, 27))

        self.assertIn("Cadência: 2/2", report)
        self.assertIn("scheduled: 2", report)

    def test_weekly_report_rejects_non_monday(self):
        from content_ops.reporting import weekly_report

        with self.assertRaisesRegex(ValueError, "Monday"):
            weekly_report(self.database, date(2026, 7, 28))

    def test_sync_marks_only_published_response_and_saves_platform_url(self):
        from content_ops.reporting import sync_published_post

        class ReadOnlyClient:
            def __init__(self):
                self.get_calls = []

            def get_post(self, post_id):
                self.get_calls.append(post_id)
                return {"status": "published", "platformPostUrl": "https://linkedin.test/posts/1"}

        client = ReadOnlyClient()
        changed = sync_published_post(client, self.database, self.scheduled)

        self.assertTrue(changed)
        self.assertEqual(client.get_calls, ["z-1"])
        with self.database._connect() as connection:
            row = connection.execute(
                "SELECT status, platform_post_url FROM posts WHERE id = ?", (self.scheduled,)
            ).fetchone()
        self.assertEqual(row["status"], "published")
        self.assertEqual(row["platform_post_url"], "https://linkedin.test/posts/1")

    def test_sync_leaves_scheduled_post_unchanged_after_nonpublished_response(self):
        from content_ops.reporting import sync_published_post

        class ReadOnlyClient:
            def get_post(self, post_id):
                return {"status": "scheduled"}

        self.assertFalse(sync_published_post(ReadOnlyClient(), self.database, self.scheduled))
        with self.database._connect() as connection:
            status = connection.execute(
                "SELECT status FROM posts WHERE id = ?", (self.scheduled,)
            ).fetchone()[0]
        self.assertEqual(status, "scheduled")

    def test_sync_does_not_publish_when_get_fails(self):
        from content_ops.reporting import sync_published_post
        from content_ops.zernio import ZernioError

        class ReadOnlyClient:
            def get_post(self, post_id):
                raise ZernioError(0, "Network error")

        with self.assertRaises(ZernioError):
            sync_published_post(ReadOnlyClient(), self.database, self.scheduled)
        with self.database._connect() as connection:
            status = connection.execute(
                "SELECT status FROM posts WHERE id = ?", (self.scheduled,)
            ).fetchone()[0]
        self.assertEqual(status, "scheduled")
