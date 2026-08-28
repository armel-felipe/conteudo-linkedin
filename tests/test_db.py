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
            PostStatus.APPROVED: (
                PostStatus.SCHEDULED,
                PostStatus.INDETERMINATE,
                PostStatus.DRAFT,
                PostStatus.FAILED,
            ),
            PostStatus.SCHEDULED: (
                PostStatus.PUBLISHED,
                PostStatus.FAILED,
                PostStatus.INDETERMINATE,
            ),
            PostStatus.FAILED: (PostStatus.APPROVED, PostStatus.ARCHIVED),
            PostStatus.INDETERMINATE: (
                PostStatus.SCHEDULED,
                PostStatus.FAILED,
                PostStatus.ARCHIVED,
            ),
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

    def test_initialize_migrates_an_idempotency_key_column(self):
        with sqlite3.connect(self.path) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(posts)")}

        self.assertIn("idempotency_key", columns)

    def test_initialize_migrates_schedule_recovery_columns_on_an_existing_database(self):
        legacy_path = Path(self.temporary_directory.name) / "legacy.db"
        with sqlite3.connect(legacy_path) as connection:
            connection.execute(
                "CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL)"
            )

        from content_ops.db import Database

        Database(legacy_path).initialize()

        with sqlite3.connect(legacy_path) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(posts)")}
        self.assertTrue({"idempotency_key", "scheduled_for", "schedule_payload"} <= columns)

    def test_initialize_versions_schema_and_migrates_legacy_posts(self):
        legacy_path = Path(self.temporary_directory.name) / "legacy-versioned.db"
        with sqlite3.connect(legacy_path) as connection:
            connection.execute(
                "CREATE TABLE posts "
                "(id INTEGER PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO posts (title, status) VALUES ('Legado', 'published')"
            )

        from content_ops.db import CURRENT_SCHEMA_VERSION, Database

        database = Database(legacy_path)
        database.initialize()
        database.upsert_post("linkedin:new", "Novo", "published")

        with sqlite3.connect(legacy_path) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(posts)")
            }
            count = connection.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        self.assertEqual(version, CURRENT_SCHEMA_VERSION)
        self.assertTrue(
            {
                "external_id",
                "created_at",
                "updated_at",
                "metrics",
                "publication_result",
                "suggested_time",
                "sources",
            }
            <= columns
        )
        self.assertEqual(count, 2)

    def test_transition_post_rejects_missing_post(self):
        from content_ops.models import PostStatus

        with self.assertRaises(ValueError):
            self.db.transition_post(999, PostStatus.DRAFT)

    def test_transaction_acquires_the_write_lock_before_reading_approval_count(self):
        with patch.object(self.db, "_begin_immediate", wraps=self.db._begin_immediate) as begin:
            with self.db.transaction() as connection:
                self.assertTrue(connection.in_transaction)

        begin.assert_called_once()

    def test_research_report_can_record_an_optional_pillar(self):
        self.db.create_research_report("Liderança", "research/lideranca.md", pillar="Liderança e gestão de times")

        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT topic, path, pillar FROM research_reports WHERE path = ?",
                ("research/lideranca.md",),
            ).fetchone()
        self.assertEqual(row[0], "Liderança")
        self.assertEqual(row[2], "Liderança e gestão de times")

    def test_research_report_without_pillar_stores_null(self):
        self.db.create_research_report("IA", "research/ia.md")

        with sqlite3.connect(self.path) as connection:
            pillar = connection.execute(
                "SELECT pillar FROM research_reports WHERE path = ?",
                ("research/ia.md",),
            ).fetchone()[0]
        self.assertIsNone(pillar)

    def test_initialize_migrates_round_and_label_columns(self):
        legacy_path = Path(self.temporary_directory.name) / "legacy-rounds.db"
        with sqlite3.connect(legacy_path) as connection:
            connection.execute(
                "CREATE TABLE research_reports ("
                "id INTEGER PRIMARY KEY, topic TEXT NOT NULL, path TEXT NOT NULL, "
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, pillar TEXT)"
            )
            connection.execute(
                "CREATE TABLE ideas ("
                "id INTEGER PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'idea', "
                "pillar_id INTEGER, research_report_id INTEGER, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute(
                "INSERT INTO research_reports (topic, path) VALUES ('IA', 'research/ia.md')"
            )

        from content_ops.db import CURRENT_SCHEMA_VERSION, Database

        Database(legacy_path).initialize()

        with sqlite3.connect(legacy_path) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            tables = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            rr_cols = {row[1] for row in connection.execute("PRAGMA table_info(research_reports)")}
            ideas_cols = {row[1] for row in connection.execute("PRAGMA table_info(ideas)")}
        self.assertEqual(version, CURRENT_SCHEMA_VERSION)
        self.assertIn("rounds", tables)
        self.assertTrue({"round_id", "label"} <= rr_cols)
        self.assertIn("sources", ideas_cols)

    def test_round_lifecycle_create_list_close(self):
        round_id = self.db.create_round("Liderança e gestão de times", "runtime/rodadas/2026-08-28.md")
        self.assertIsInstance(round_id, int)

        rounds = self.db.list_rounds()
        self.assertEqual(len(rounds), 1)
        self.assertEqual(rounds[0]["pillar"], "Liderança e gestão de times")
        self.assertEqual(rounds[0]["status"], "open")

        self.db.close_round(round_id)
        self.assertEqual(self.db.list_rounds()[0]["status"], "closed")

    def test_research_report_records_round_and_label(self):
        round_id = self.db.create_round("Liderança e gestão de times", "runtime/rodadas/x.md")
        self.db.create_research_report(
            "liderança em times de alta performance",
            "research/lideranca-times.md",
            pillar="Liderança e gestão de times",
            round_id=round_id,
            label="2026_08_28 lideranca-gestao-times cultura-times-alta-perf",
        )

        reports = self.db.list_research_reports()
        self.assertEqual(len(reports), 1)
        topic, path, pillar, rid, label = reports[0]
        self.assertEqual(rid, round_id)
        self.assertEqual(label, "2026_08_28 lideranca-gestao-times cultura-times-alta-perf")

    def test_initialize_migrates_pillar_column_on_an_existing_database(self):
        legacy_path = Path(self.temporary_directory.name) / "legacy-research.db"
        with sqlite3.connect(legacy_path) as connection:
            connection.execute(
                "CREATE TABLE research_reports ("
                "id INTEGER PRIMARY KEY, topic TEXT NOT NULL, path TEXT NOT NULL, "
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute(
                "INSERT INTO research_reports (topic, path) VALUES ('IA', 'research/ia.md')"
            )

        from content_ops.db import Database

        Database(legacy_path).initialize()

        with sqlite3.connect(legacy_path) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(research_reports)")}
            pillar = connection.execute(
                "SELECT pillar FROM research_reports WHERE path = ?", ("research/ia.md",)
            ).fetchone()[0]
        self.assertIn("pillar", columns)
        self.assertIsNone(pillar)


if __name__ == "__main__":
    unittest.main()
