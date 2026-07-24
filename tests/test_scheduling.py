import argparse
import json
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
        self.idempotency_keys = []

    def create_post(self, payload, idempotency_key):
        self.create_calls += 1
        self.payloads.append(payload)
        self.idempotency_keys.append(idempotency_key)
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

    def schedule(self, client=None):
        from content_ops.workflow import schedule_post

        return schedule_post(
            self.post_id,
            self.path,
            "2026-08-01T10:00:00",
            True,
            client or self.client,
            database=self.database,
            account_id="linkedin-account",
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_schedule_requires_both_approvals(self):
        from content_ops.workflow import SchedulingValidationError, schedule_post

        with self.assertRaises(SchedulingValidationError):
            self.schedule()

        self.assertEqual(self.client.create_calls, 0)

    def test_schedule_calls_client_only_after_confirmation(self):
        from content_ops.markdown import read_post_record
        from content_ops.workflow import approve_draft, schedule_post

        approve_draft(self.post_id, self.path, database=self.database)

        self.assertEqual(
            self.schedule(),
            "z-1",
        )
        self.assertEqual(self.client.create_calls, 1)
        self.assertEqual(self.client.payloads, [{
            "content": "Texto aprovado.",
            "scheduledFor": "2026-08-01T10:00:00",
            "timezone": "America/Sao_Paulo",
            "targets": [{"platform": "linkedin", "accountId": "linkedin-account"}],
        }])
        self.assertEqual(read_post_record(self.path)[0]["zernio_post_id"], "z-1")

    def test_schedule_persists_uuid_idempotency_key_before_posting(self):
        from content_ops.markdown import read_post_record
        from content_ops.workflow import approve_draft
        from uuid import UUID

        approve_draft(self.post_id, self.path, database=self.database)
        observed = {}

        class InspectingClient(FakeClient):
            def create_post(client_self, payload, idempotency_key):
                metadata, _ = read_post_record(self.path)
                with self.database._connect() as connection:
                    stored = connection.execute(
                        "SELECT idempotency_key FROM posts WHERE id = ?", (self.post_id,)
                    ).fetchone()[0]
                observed.update(markdown=metadata["idempotency_key"], database=stored)
                return super().create_post(payload, idempotency_key)

        client = InspectingClient()
        self.assertEqual(self.schedule(client), "z-1")
        UUID(client.idempotency_keys[0])
        self.assertEqual(observed["markdown"], client.idempotency_keys[0])
        self.assertEqual(observed["database"], client.idempotency_keys[0])

    def test_uncertain_result_becomes_indeterminate_and_reconcile_reuses_key(self):
        from content_ops.markdown import read_post_record
        from content_ops.workflow import (
            SchedulingError,
            approve_draft,
            reconcile_schedule,
        )
        from content_ops.zernio import ZernioUncertainError

        approve_draft(self.post_id, self.path, database=self.database)
        uncertain = FakeClient(error=ZernioUncertainError("connection closed"))
        with self.assertRaisesRegex(SchedulingError, "requires reconciliation"):
            self.schedule(uncertain)
        self.assertEqual(read_post_record(self.path)[0]["status"], "indeterminate")
        first_key = uncertain.idempotency_keys[0]

        with self.assertRaisesRegex(SchedulingError, "requires reconciliation"):
            self.schedule(uncertain)
        self.assertEqual(uncertain.create_calls, 1)

        recovered = FakeClient(response="z-recovered")
        self.assertEqual(
            reconcile_schedule(self.post_id, self.path, recovered, database=self.database,
                               account_id="linkedin-account"),
            "z-recovered",
        )
        self.assertEqual(recovered.idempotency_keys, [first_key])
        self.assertEqual(read_post_record(self.path)[0]["status"], "scheduled")

    def test_confirmed_pre_send_failure_becomes_failed(self):
        from content_ops.markdown import read_post_record
        from content_ops.workflow import SchedulingError, approve_draft
        from content_ops.zernio import ZernioPreSendError

        approve_draft(self.post_id, self.path, database=self.database)
        with self.assertRaisesRegex(SchedulingError, "Scheduling request failed"):
            self.schedule(FakeClient(error=ZernioPreSendError("request was not sent")))
        self.assertEqual(read_post_record(self.path)[0]["status"], "failed")

    def test_http_500_response_becomes_indeterminate(self):
        from content_ops.markdown import read_post_record
        from content_ops.workflow import SchedulingError, approve_draft
        from content_ops.zernio import ZernioError

        approve_draft(self.post_id, self.path, database=self.database)
        with self.assertRaisesRegex(SchedulingError, "requires reconciliation"):
            self.schedule(FakeClient(error=ZernioError(500, "HTTP 500 error")))

        self.assertEqual(read_post_record(self.path)[0]["status"], "indeterminate")

    def test_schedule_rejects_invalid_persisted_uuid_before_http(self):
        from content_ops.markdown import read_post_record, write_post_record
        from content_ops.workflow import SchedulingError, approve_draft

        approve_draft(self.post_id, self.path, database=self.database)
        metadata, body = read_post_record(self.path)
        metadata["idempotency_key"] = "not-a-uuid"
        write_post_record(self.path, metadata, body)

        with self.assertRaisesRegex(SchedulingError, "Scheduling recovery is required"):
            self.schedule()
        self.assertEqual(self.client.create_calls, 0)

    def test_reconcile_rejects_invalid_persisted_uuid_before_http(self):
        from content_ops.markdown import read_post_record, write_post_record
        from content_ops.models import PostStatus
        from content_ops.workflow import SchedulingError, approve_draft, reconcile_schedule

        approve_draft(self.post_id, self.path, database=self.database)
        self.database.persist_schedule_intent(
            self.post_id,
            "not-a-uuid",
            "2026-08-01T10:00:00",
            {"content": "Texto aprovado."},
        )
        metadata, body = read_post_record(self.path)
        metadata["status"] = "indeterminate"
        write_post_record(self.path, metadata, body)
        self.database.record_schedule_result(self.post_id, PostStatus.INDETERMINATE, None)

        with self.assertRaisesRegex(SchedulingError, "Scheduling recovery is required"):
            reconcile_schedule(self.post_id, self.path, self.client, database=self.database)
        self.assertEqual(self.client.create_calls, 0)

    def test_schedule_rejects_missing_confirmation_before_http(self):
        from content_ops.workflow import SchedulingValidationError, approve_draft, schedule_post

        approve_draft(self.post_id, self.path, database=self.database)
        with self.assertRaisesRegex(SchedulingValidationError, "--confirm is required"):
            schedule_post(
                self.post_id, self.path, "2026-08-01T10:00:00", False, self.client,
                database=self.database, account_id="linkedin-account",
            )
        self.assertEqual(self.client.create_calls, 0)

    def test_schedule_rejects_past_time_before_http(self):
        from content_ops.workflow import SchedulingValidationError, approve_draft, schedule_post

        approve_draft(self.post_id, self.path, database=self.database)
        past = (datetime.now() - timedelta(minutes=1)).isoformat(timespec="minutes")
        with self.assertRaises(SchedulingValidationError):
            schedule_post(self.post_id, self.path, past, True, self.client, database=self.database,
                          account_id="linkedin-account")
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
            self.schedule()
        self.assertEqual(self.client.create_calls, 0)

    def test_schedule_includes_media_only_for_http_image_url(self):
        from content_ops.markdown import read_post_record, write_post_record
        from content_ops.workflow import approve_draft, schedule_post

        metadata, body = read_post_record(self.path)
        metadata["image_url"] = "https://example.test/post.png"
        write_post_record(self.path, metadata, body)
        approve_draft(self.post_id, self.path, database=self.database)

        self.schedule()

        self.assertEqual(self.client.payloads[0]["mediaItems"], [{"url": "https://example.test/post.png"}])

    def test_unknown_client_error_marks_post_indeterminate_without_retry(self):
        from content_ops.markdown import read_post_record
        from content_ops.workflow import SchedulingError, approve_draft, schedule_post

        approve_draft(self.post_id, self.path, database=self.database)
        failing_client = FakeClient(error=RuntimeError("secret detail"))
        with self.assertRaisesRegex(SchedulingError, "requires reconciliation"):
            self.schedule(failing_client)

        self.assertEqual(failing_client.create_calls, 1)
        self.assertEqual(read_post_record(self.path)[0]["status"], "indeterminate")
        with self.database._connect() as connection:
            status = connection.execute("SELECT status FROM posts WHERE id = ?", (self.post_id,)).fetchone()[0]
        self.assertEqual(status, "indeterminate")

    def test_schedule_rejects_https_url_without_host_before_http(self):
        from content_ops.markdown import read_post_record, write_post_record
        from content_ops.workflow import SchedulingValidationError, approve_draft

        metadata, body = read_post_record(self.path)
        metadata["image_url"] = "https:"
        write_post_record(self.path, metadata, body)
        approve_draft(self.post_id, self.path, database=self.database)

        with self.assertRaisesRegex(SchedulingValidationError, "image_url must use HTTP\\(S\\)"):
            self.schedule()
        self.assertEqual(self.client.create_calls, 0)

    def test_intent_write_failure_aborts_before_http_without_a_sidecar(self):
        from content_ops.workflow import SchedulingError, approve_draft

        approve_draft(self.post_id, self.path, database=self.database)
        with patch("content_ops.workflow.write_post_record", side_effect=OSError("markdown secret")):
            with self.assertRaisesRegex(SchedulingError, "Could not persist scheduling request") as raised:
                self.schedule(self.client)

        self.assertNotIn("secret", str(raised.exception))
        self.assertEqual(self.client.create_calls, 0)
        recovery_path = self.path.with_name(f".{self.path.name}.schedule-recovery.json")
        self.assertFalse(recovery_path.exists())
        with self.database._connect() as connection:
            key = connection.execute(
                "SELECT idempotency_key FROM posts WHERE id = ?", (self.post_id,)
            ).fetchone()[0]
        self.assertIsNotNone(key)

    def test_result_persistence_failure_is_indeterminate_in_markdown_not_only_sidecar(self):
        from content_ops.markdown import read_post_record
        from content_ops.workflow import SchedulingError, approve_draft

        approve_draft(self.post_id, self.path, database=self.database)
        with patch.object(self.database, "record_schedule_result", side_effect=OSError("db unavailable")):
            with self.assertRaisesRegex(SchedulingError, "requires reconciliation"):
                self.schedule()

        self.assertEqual(read_post_record(self.path)[0]["status"], "indeterminate")

    def test_schedule_persists_zernio_id_in_sqlite(self):
        from content_ops.workflow import approve_draft

        approve_draft(self.post_id, self.path, database=self.database)
        self.schedule()

        with self.database._connect() as connection:
            zernio_post_id = connection.execute(
                "SELECT zernio_post_id FROM posts WHERE id = ?", (self.post_id,)
            ).fetchone()[0]
        self.assertEqual(zernio_post_id, "z-1")

    def test_zernio_client_sends_persisted_key_as_x_request_id(self):
        from content_ops.zernio import ZernioClient

        captured = {}

        class Response:
            def read(self):
                return b'{"id":"z-1"}'

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        def opener(request):
            captured["request"] = request
            return Response()

        client = ZernioClient("local-test-key", opener=opener)
        self.assertEqual(client.create_post({"content": "x"}, "request-uuid"), "z-1")
        self.assertEqual(captured["request"].get_header("X-request-id"), "request-uuid")

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

    def test_cli_parser_accepts_schedule_reconcile_syntax(self):
        from content_ops.cli import build_parser

        arguments = build_parser().parse_args(["schedule", "reconcile", "7"])

        self.assertEqual(arguments.post_id, "reconcile")
        self.assertEqual(arguments.reconcile_post_id, "7")


if __name__ == "__main__":
    unittest.main()
