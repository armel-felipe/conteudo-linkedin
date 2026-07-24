import json
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError


def exception_chain(error):
    """Return explicit exception links without following traceback frames."""
    chain = []
    while error is not None:
        chain.append(error)
        error = error.__cause__ or error.__context__
    return chain


class FakeZernioClient:
    def list_external_posts(self, account_id):
        self.account_id = account_id
        from content_ops.zernio import ExternalPosts

        return ExternalPosts(
            [{"_id": "a1", "content": "Python e dados", "status": "published"}],
            [b'[{"_id":"a1","content":"Python e dados","status":"published"}]'],
        )


class HistoryImportTests(unittest.TestCase):
    def setUp(self):
        from content_ops.db import Database

        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.import_dir = root / "imports"
        self.db = Database(root / "content.db")
        self.db.initialize()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_import_writes_one_row_and_snapshot(self):
        from content_ops.history import import_history

        client = FakeZernioClient()
        import_history(client, self.db, "account", self.import_dir)

        self.assertEqual(client.account_id, "account")
        self.assertEqual(self.db.count_posts(), 1)
        snapshots = list(self.import_dir.glob("*.json"))
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(
            snapshots[0].read_bytes(),
            b'[{"_id":"a1","content":"Python e dados","status":"published"}]',
        )

    def test_import_is_idempotent(self):
        from content_ops.history import import_history

        client = FakeZernioClient()
        import_history(client, self.db, "account", self.import_dir)
        import_history(client, self.db, "account", self.import_dir)

        self.assertEqual(self.db.count_posts(), 1)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class ZernioClientTests(unittest.TestCase):
    def test_list_external_posts_paginates_and_uses_bearer_authentication(self):
        from content_ops.zernio import ZernioClient

        requests = []
        first_page = [{"_id": str(index)} for index in range(100)]
        responses = iter(
            [
                FakeResponse(json.dumps(first_page).encode("utf-8")),
                FakeResponse(b'[{"_id":"last"}]'),
            ]
        )

        def opener(request):
            requests.append(request)
            return next(responses)

        posts = ZernioClient("test-key", base_url="https://zernio.test", opener=opener)
        result = posts.list_external_posts("account id")

        self.assertEqual(len(result), 101)
        self.assertEqual(len(result.pages), 2)
        self.assertEqual(requests[0].get_header("Authorization"), "Bearer test-key")
        self.assertIn("source=external", requests[0].full_url)
        self.assertIn("accountId=account+id", requests[0].full_url)
        self.assertIn("page=1", requests[0].full_url)
        self.assertIn("page=2", requests[1].full_url)

    def test_list_external_posts_retains_unmodified_raw_page_bytes(self):
        from content_ops.zernio import ZernioClient

        raw_page = b'[ { "_id" : "a1", "content" : "caf\\u00e9" } ]\n'
        result = ZernioClient(
            "test-key", opener=lambda request: FakeResponse(raw_page)
        ).list_external_posts("account")

        self.assertEqual(result.pages, [raw_page])
        self.assertEqual(result[0]["content"], "caf\u00e9")

    def test_list_external_posts_raises_for_invalid_json(self):
        from content_ops.zernio import ZernioClient, ZernioError

        client = ZernioClient("test-key", opener=lambda request: FakeResponse(b"not json"))

        with self.assertRaisesRegex(ZernioError, "Invalid JSON"):
            client.list_external_posts("account")

    def test_list_external_posts_does_not_expose_http_error_body(self):
        from content_ops.zernio import ZernioClient, ZernioError

        error = HTTPError(
            "https://zernio.test/api/v1/posts",
            401,
            "Unauthorized",
            None,
            io.BytesIO(b'{"message": "invalid credentials: secret server detail"}'),
        )
        client = ZernioClient("test-key", opener=lambda request: (_ for _ in ()).throw(error))

        with self.assertRaises(ZernioError) as raised:
            client.list_external_posts("account")

        self.assertEqual(raised.exception.status, 401)
        self.assertEqual(raised.exception.message, "HTTP 401 error")
        self.assertNotIn("credentials", str(raised.exception))
        self.assertNotIn("secret server detail", str(raised.exception))
        self.assertIsNone(raised.exception.__cause__)
        self.assertIsNone(raised.exception.__context__)
        self.assertFalse(
            any(
                "secret server detail" in str(error)
                for error in exception_chain(raised.exception)
            )
        )

    def test_list_external_posts_does_not_expose_url_error_reason(self):
        from content_ops.zernio import ZernioClient, ZernioError

        client = ZernioClient(
            "test-key",
            opener=lambda request: (_ for _ in ()).throw(
                URLError("proxy returned internal hostname: sensitive.example")
            ),
        )

        with self.assertRaises(ZernioError) as raised:
            client.list_external_posts("account")

        self.assertEqual(raised.exception.status, 0)
        self.assertEqual(raised.exception.message, "Network error")
        self.assertNotIn("sensitive.example", str(raised.exception))
        self.assertIsNone(raised.exception.__cause__)
        self.assertIsNone(raised.exception.__context__)
        self.assertFalse(
            any(
                "sensitive.example" in str(error)
                for error in exception_chain(raised.exception)
            )
        )


class HistoryCommandTests(unittest.TestCase):
    def test_history_import_reports_missing_configuration_without_network(self):
        from content_ops.cli import main

        stderr = io.StringIO()
        with (
            patch("content_ops.cli.load_env"),
            patch.dict(os.environ, {}, clear=True),
            redirect_stderr(stderr),
            self.assertRaises(SystemExit) as raised,
        ):
            main(["history", "import"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("ZERNIO_API_KEY", stderr.getvalue())
        self.assertIn("ZERNIO_ACCOUNT_ID", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
