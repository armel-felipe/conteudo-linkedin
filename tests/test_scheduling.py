import argparse
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch


class FakeClient:
    def __init__(self, response="z-1", error=None):
        self.response = response
        self.error = error
        self.create_calls = 0
        self.payloads = []

    def create_post(self, payload):
        self.create_calls += 1
        self.payloads.append(payload)
        if self.error:
            raise self.error
        return self.response


class SchedulingTests(unittest.TestCase):
    def setUp(self):
        from content_ops.db import Database
        from content_ops.markdown import write_post_record

        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.database = Database(self.root / "content.db")
        self.database.initialize()
        self.database.upsert_pillar("IA aplicada")
        self.database.approve_pillar("IA aplicada")
        self.post_id = self.database.create_post("in_review", "Post")
        self.path = self.root / "draft.md"
        write_post_record(
            self.path,
            {"approved": False, "image_url": None, "pillar": "IA aplicada", "status": "in_review", "zernio_post_id": None},
            "Texto aprovado.",
        )
        self.client = FakeClient()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_schedule_requires_both_approvals(self):
        from content_ops.workflow import SchedulingValidationError, schedule_post

        with self.assertRaises(SchedulingValidationError):
            schedule_post(
                self.post_id, self.path, "2026-08-01T10:00:00", True, self.client,
                database=self.database,
            )

        self.assertEqual(self.client.create_calls, 0)

    def test_schedule_calls_client_only_after_confirmation(self):
        from content_ops.markdown import read_post_record
        from content_ops.workflow import approve_draft, schedule_post

        approve_draft(self.post_id, self.path, database=self.database)

        self.assertEqual(
            schedule_post(
                self.post_id, self.path, "2026-08-01T10:00:00", True, self.client,
                database=self.database,
            ),
            "z-1",
        )
        self.assertEqual(self.client.create_calls, 1)
        self.assertEqual(self.client.payloads, [{
            "content": "Texto aprovado.",
            "scheduledFor": "2026-08-01T10:00:00",
            "timezone": "America/Sao_Paulo",
            "targets": [{"platform": "linkedin"}],
        }])
        self.assertEqual(read_post_record(self.path)[0]["zernio_post_id"], "z-1")

    def test_schedule_rejects_missing_confirmation_before_http(self):
        from content_ops.workflow import SchedulingValidationError, approve_draft, schedule_post

        approve_draft(self.post_id, self.path, database=self.database)
        with self.assertRaisesRegex(SchedulingValidationError, "--confirm is required"):
            schedule_post(
                self.post_id, self.path, "2026-08-01T10:00:00", False, self.client,
                database=self.database,
            )
        self.assertEqual(self.client.create_calls, 0)

    def test_schedule_rejects_past_time_before_http(self):
        from content_ops.workflow import SchedulingValidationError, approve_draft, schedule_post

        approve_draft(self.post_id, self.path, database=self.database)
        past = (datetime.now() - timedelta(minutes=1)).isoformat(timespec="minutes")
        with self.assertRaises(SchedulingValidationError):
            schedule_post(self.post_id, self.path, past, True, self.client, database=self.database)
        self.assertEqual(self.client.create_calls, 0)

    def test_schedule_rejects_empty_body_before_http(self):
        from content_ops.workflow import SchedulingValidationError, approve_draft, schedule_post

        approve_draft(self.post_id, self.path, database=self.database)
        self.path.write_text(
            '---json\n{"approved": true, "image_url": null, "pillar": "IA aplicada", '
            '"status": "approved", "zernio_post_id": null}\n---\n\n',
            encoding="utf-8",
        )
        with self.assertRaises(SchedulingValidationError):
            schedule_post(
                self.post_id, self.path, "2026-08-01T10:00:00", True, self.client,
                database=self.database,
            )
        self.assertEqual(self.client.create_calls, 0)

    def test_schedule_includes_media_only_for_http_image_url(self):
        from content_ops.markdown import read_post_record, write_post_record
        from content_ops.workflow import approve_draft, schedule_post

        metadata, body = read_post_record(self.path)
        metadata["image_url"] = "https://example.test/post.png"
        write_post_record(self.path, metadata, body)
        approve_draft(self.post_id, self.path, database=self.database)

        schedule_post(self.post_id, self.path, "2026-08-01T10:00:00", True, self.client, database=self.database)

        self.assertEqual(self.client.payloads[0]["mediaItems"], [{"url": "https://example.test/post.png"}])

    def test_client_error_marks_post_failed_without_retry(self):
        from content_ops.markdown import read_post_record
        from content_ops.workflow import SchedulingError, approve_draft, schedule_post

        approve_draft(self.post_id, self.path, database=self.database)
        failing_client = FakeClient(error=RuntimeError("secret detail"))
        with self.assertRaisesRegex(SchedulingError, "Scheduling request failed"):
            schedule_post(self.post_id, self.path, "2026-08-01T10:00:00", True, failing_client, database=self.database)

        self.assertEqual(failing_client.create_calls, 1)
        self.assertEqual(read_post_record(self.path)[0]["status"], "failed")
        with self.database._connect() as connection:
            status = connection.execute("SELECT status FROM posts WHERE id = ?", (self.post_id,)).fetchone()[0]
        self.assertEqual(status, "failed")

    def test_approval_restores_database_status_when_markdown_write_fails(self):
        from content_ops.workflow import approve_draft

        with patch("content_ops.workflow.write_post_record", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                approve_draft(self.post_id, self.path, database=self.database)

        with self.database._connect() as connection:
            status = connection.execute("SELECT status FROM posts WHERE id = ?", (self.post_id,)).fetchone()[0]
        self.assertEqual(status, "in_review")

    def test_cli_requires_confirm_before_loading_zernio_configuration(self):
        from content_ops.cli import main

        with patch.dict("os.environ", {}, clear=True):
            with patch.object(argparse.ArgumentParser, "error", side_effect=RuntimeError) as error:
                with self.assertRaises(RuntimeError):
                    main(["schedule", "1", "--at", "2026-08-01T10:00:00"])
        self.assertEqual(error.call_args.args[0], "--confirm is required")


if __name__ == "__main__":
    unittest.main()
