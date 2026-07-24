import tempfile
import unittest
from pathlib import Path


class MarkdownRecordTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "post.md"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_round_trips_metadata_and_body(self):
        from content_ops.markdown import read_post_record, write_post_record

        write_post_record(self.path, {"status": "approved", "approved": True}, "Texto")

        metadata, body = read_post_record(self.path)

        self.assertTrue(metadata["approved"])
        self.assertEqual(body, "Texto")

    def test_writes_equivalent_metadata_deterministically(self):
        from content_ops.markdown import write_post_record

        second_path = Path(self.temporary_directory.name) / "second-post.md"
        write_post_record(self.path, {"status": "approved", "approved": True}, "Texto")
        write_post_record(second_path, {"approved": True, "status": "approved"}, "Texto")

        self.assertEqual(self.path.read_text(encoding="utf-8"), second_path.read_text(encoding="utf-8"))

    def test_rejects_missing_delimiters(self):
        from content_ops.markdown import read_post_record

        self.path.write_text('{"status": "approved"}\n\nTexto\n', encoding="utf-8")

        with self.assertRaises(ValueError):
            read_post_record(self.path)

    def test_rejects_metadata_that_is_not_a_json_object(self):
        from content_ops.markdown import read_post_record

        self.path.write_text('---json\n["approved"]\n---\n\nTexto\n', encoding="utf-8")

        with self.assertRaises(ValueError):
            read_post_record(self.path)

    def test_rejects_empty_body(self):
        from content_ops.markdown import read_post_record

        self.path.write_text('---json\n{}\n---\n\n   \n', encoding="utf-8")

        with self.assertRaises(ValueError):
            read_post_record(self.path)


if __name__ == "__main__":
    unittest.main()
