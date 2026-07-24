import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch


class ReportingTests(unittest.TestCase):
    def setUp(self):
        from content_ops.db import Database
        from content_ops.models import PostStatus

        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temporary_directory.name) / "content.db")
        self.database.initialize()
        today = date.today()
        self.week_start = today + timedelta(days=(7 - today.weekday()) % 7)
        scheduled_for = (
            f"{self.week_start.isoformat()}T10:00:00-03:00"
        )
        published_for = (
            f"{(self.week_start + timedelta(days=5)).isoformat()}T10:00:00-03:00"
        )
        self.scheduled = self.database.create_post(PostStatus.APPROVED, "Scheduled post")
        self.database.persist_schedule_intent(
            self.scheduled, "123e4567-e89b-12d3-a456-426614174000",
            scheduled_for, {"content": "Scheduled post"},
        )
        self.database.record_schedule_result(self.scheduled, PostStatus.SCHEDULED, "z-1")
        self.published = self.database.create_post(PostStatus.APPROVED, "Published post")
        self.database.persist_schedule_intent(
            self.published, "123e4567-e89b-12d3-a456-426614174001",
            published_for, {"content": "Published post"},
        )
        self.database.record_schedule_result(self.published, PostStatus.SCHEDULED, "z-2")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_weekly_report_counts_cadence(self):
        from content_ops.reporting import weekly_report

        report = weekly_report(self.database, self.week_start)

        self.assertIn("Cadência: 2/2", report)
        self.assertIn("scheduled: 2", report)

    def test_weekly_report_rejects_non_monday(self):
        from content_ops.reporting import weekly_report

        with self.assertRaisesRegex(ValueError, "Monday"):
            weekly_report(self.database, self.week_start + timedelta(days=1))

    def test_sync_marks_only_published_response_and_saves_platform_url(self):
        from content_ops.markdown import read_post_record, write_post_record
        from content_ops.reporting import sync_published_post

        class ReadOnlyClient:
            def __init__(self):
                self.get_calls = []

            def get_post(self, post_id):
                self.get_calls.append(post_id)
                return {
                    "status": "published",
                    "platformPostUrl": "https://linkedin.test/posts/1",
                    "metrics": {"impressions": 1200, "likes": 42, "comments": 3},
                }

        client = ReadOnlyClient()
        path = Path(self.temporary_directory.name) / "scheduled.md"
        write_post_record(
            path,
            {"post_id": self.scheduled, "status": "scheduled", "published_url": None},
            "Conteúdo",
        )
        changed = sync_published_post(client, self.database, self.scheduled, path)

        self.assertTrue(changed)
        self.assertEqual(client.get_calls, ["z-1"])
        with self.database._connect() as connection:
            row = connection.execute(
                "SELECT status, platform_post_url, metrics, publication_result "
                "FROM posts WHERE id = ?",
                (self.scheduled,),
            ).fetchone()
        self.assertEqual(row["status"], "published")
        self.assertEqual(row["platform_post_url"], "https://linkedin.test/posts/1")
        self.assertEqual(
            json.loads(row["metrics"]),
            {"comments": 3, "impressions": 1200, "likes": 42},
        )
        self.assertEqual(json.loads(row["publication_result"])["status"], "published")
        metadata, _ = read_post_record(path)
        self.assertEqual(metadata["status"], "published")
        self.assertEqual(metadata["published_url"], "https://linkedin.test/posts/1")
        self.assertEqual(metadata["metrics"]["impressions"], 1200)
        self.assertEqual(metadata["publication_result"]["status"], "published")

    def test_sync_leaves_scheduled_post_unchanged_after_nonpublished_response(self):
        from content_ops.markdown import write_post_record
        from content_ops.reporting import sync_published_post

        class ReadOnlyClient:
            def get_post(self, post_id):
                return {"status": "scheduled"}

        path = Path(self.temporary_directory.name) / "scheduled.md"
        write_post_record(
            path, {"post_id": self.scheduled, "status": "scheduled"}, "Conteúdo"
        )
        self.assertFalse(
            sync_published_post(ReadOnlyClient(), self.database, self.scheduled, path)
        )
        with self.database._connect() as connection:
            status = connection.execute(
                "SELECT status FROM posts WHERE id = ?", (self.scheduled,)
            ).fetchone()[0]
        self.assertEqual(status, "scheduled")

    def test_sync_maps_remote_failed_to_failed_in_both_stores(self):
        from content_ops.markdown import read_post_record, write_post_record
        from content_ops.reporting import sync_published_post

        class ReadOnlyClient:
            def get_post(self, post_id):
                return {"status": "FAILED"}

        path = Path(self.temporary_directory.name) / "scheduled.md"
        write_post_record(
            path, {"post_id": self.scheduled, "status": "scheduled"}, "Conteúdo"
        )

        self.assertFalse(
            sync_published_post(ReadOnlyClient(), self.database, self.scheduled, path)
        )

        with self.database._connect() as connection:
            status = connection.execute(
                "SELECT status FROM posts WHERE id = ?", (self.scheduled,)
            ).fetchone()[0]
        self.assertEqual(status, "failed")
        metadata, _ = read_post_record(path)
        self.assertEqual(metadata["status"], "failed")
        self.assertEqual(metadata["publication_result"]["status"], "FAILED")

    def test_sync_does_not_publish_when_get_fails(self):
        from content_ops.markdown import write_post_record
        from content_ops.reporting import sync_published_post
        from content_ops.zernio import ZernioError

        class ReadOnlyClient:
            def get_post(self, post_id):
                raise ZernioError(0, "Network error")

        path = Path(self.temporary_directory.name) / "scheduled.md"
        write_post_record(
            path, {"post_id": self.scheduled, "status": "scheduled"}, "Conteúdo"
        )
        with self.assertRaises(ZernioError):
            sync_published_post(
                ReadOnlyClient(), self.database, self.scheduled, path
            )
        with self.database._connect() as connection:
            status = connection.execute(
                "SELECT status FROM posts WHERE id = ?", (self.scheduled,)
            ).fetchone()[0]
        self.assertEqual(status, "scheduled")

    def test_sync_markdown_failure_rolls_back_sqlite(self):
        from content_ops.markdown import write_post_record
        from content_ops.reporting import sync_published_post

        class ReadOnlyClient:
            def get_post(self, post_id):
                return {
                    "status": "published",
                    "platformPostUrl": "https://linkedin.test/posts/1",
                }

        path = Path(self.temporary_directory.name) / "scheduled.md"
        write_post_record(
            path, {"post_id": self.scheduled, "status": "scheduled"}, "Conteúdo"
        )
        with patch(
            "content_ops.reporting.write_post_record",
            side_effect=OSError("disk full"),
        ):
            with self.assertRaises(OSError):
                sync_published_post(
                    ReadOnlyClient(), self.database, self.scheduled, path
                )

        with self.database._connect() as connection:
            row = connection.execute(
                "SELECT status, platform_post_url FROM posts WHERE id = ?",
                (self.scheduled,),
            ).fetchone()
        self.assertEqual(row["status"], "scheduled")
        self.assertIsNone(row["platform_post_url"])

    def test_sync_commit_failure_restores_original_markdown(self):
        from content_ops.markdown import read_post_record, write_post_record
        from content_ops.reporting import sync_published_post

        class ReadOnlyClient:
            def get_post(self, post_id):
                return {
                    "status": "published",
                    "platformPostUrl": "https://linkedin.test/posts/1",
                }

        path = Path(self.temporary_directory.name) / "scheduled.md"
        write_post_record(
            path, {"post_id": self.scheduled, "status": "scheduled"}, "Conteúdo"
        )
        with patch.object(
            self.database, "_commit", side_effect=OSError("commit failed")
        ):
            with self.assertRaises(OSError):
                sync_published_post(
                    ReadOnlyClient(), self.database, self.scheduled, path
                )

        self.assertEqual(read_post_record(path)[0]["status"], "scheduled")
        with self.database._connect() as connection:
            status = connection.execute(
                "SELECT status FROM posts WHERE id = ?", (self.scheduled,)
            ).fetchone()[0]
        self.assertEqual(status, "scheduled")
