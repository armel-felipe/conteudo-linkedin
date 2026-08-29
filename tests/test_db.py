import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        from content_ops.db import Database

        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "data" / "content.db"
        self.db = Database(self.path)
        self.db.initialize()
        self.artifact = self.path.parent.parent / "content" / "drafts" / "x.md"
        self.artifact.parent.mkdir(parents=True)
        self.artifact.write_text("draft", encoding="utf-8")

    def complete_prior_blocks(self, round_id, blocks):
        import json
        from content_ops.orchestration import complete_block, record_review, start_block_cycle

        result = json.dumps({
            "decision": "approved",
            "artifact": "content/drafts/x.md",
            "feedback": [],
            "checks": [{"name": "quality", "status": "pass", "evidence": "ok"}],
        })
        for block in blocks:
            start_block_cycle(self.db, round_id, block, "content/drafts/x.md")
            record_review(self.db, round_id, block, "content/drafts/x.md", 1, "revisor", result)
            complete_block(self.db, round_id, block, "content/drafts/x.md", 1)

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

    def test_initialize_creates_orchestration_tables(self):
        with sqlite3.connect(self.path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

        self.assertTrue({"workflow_events", "review_receipts"} <= tables)

    def test_orchestration_writes_are_durable(self):
        round_id = self.db.create_round("Pilar", "runtime/rodadas/1.md")
        self.complete_prior_blocks(round_id, ("B1", "B2", "B3", "B4"))
        cycle_id = self.db.start_block_cycle(round_id, "B5", "content/drafts/x.md")
        result = '{"decision":"feedback","artifact":"content/drafts/x.md","feedback":[],"checks":[{"name":"quality","status":"pass","evidence":"ok"}]}'
        self.db.record_review_result(
            cycle_id, "cruzamento-revisor", "feedback", result
        )
        with sqlite3.connect(self.path) as connection:
            self.assertIsNotNone(
                connection.execute(
                    "SELECT 1 FROM review_receipts WHERE cycle_id = ?", (cycle_id,)
                ).fetchone()
            )
            self.assertEqual(connection.execute(
                "SELECT event FROM workflow_events WHERE round_id = ? AND block = ? ORDER BY id DESC LIMIT 1",
                (round_id, "B5"),
            ).fetchone()[0], "cycle_started")

    def test_orchestration_review_approval_is_scoped_to_round_block_artifact_and_cycle(self):
        round_id = self.db.create_round("Pilar", "runtime/rodadas/1.md")
        self.complete_prior_blocks(round_id, ("B1", "B2", "B3", "B4"))
        cycle_id = self.db.start_block_cycle(round_id, "B5", "content/drafts/x.md")
        result = '{"decision":"approved","artifact":"content/drafts/x.md","feedback":[],"checks":[{"name":"quality","status":"pass","evidence":"ok"}]}'
        self.db.record_review_result(
            cycle_id, "cruzamento-revisor", "approved", result
        )

        self.assertTrue(
            self.db.review_is_approved(round_id, "B5", "content/drafts/x.md", 1)
        )
        self.assertFalse(self.db.review_is_approved(round_id, "B6", "content/drafts/x.md", 1))
        self.assertFalse(self.db.review_is_approved(round_id, "B5", "other.md", 1))
        self.assertFalse(self.db.review_is_approved(round_id, "B5", "content/drafts/x.md", 2))

    def test_orchestration_constraints_reject_invalid_decision_and_json(self):
        round_id = self.db.create_round("Pilar", "runtime/rodadas/1.md")
        self.complete_prior_blocks(round_id, ("B1", "B2", "B3", "B4"))
        cycle_id = self.db.start_block_cycle(round_id, "B5", "content/drafts/x.md")

        with self.assertRaises(ValueError):
            self.db.record_review_result(cycle_id, "revisor", "unknown", "{}")
        with self.assertRaises(ValueError):
            self.db.record_review_result(cycle_id, "revisor", "approved", "not-json")
        with self.assertRaises(ValueError):
            self.db.record_workflow_event(round_id, "B5", "bad_payload", "not-json")

    def test_orchestration_constraints_enforce_uniqueness_and_foreign_keys(self):
        round_id = self.db.create_round("Pilar", "runtime/rodadas/1.md")
        self.complete_prior_blocks(round_id, ("B1", "B2", "B3", "B4"))
        cycle_id = self.db.start_block_cycle(round_id, "B5", "content/drafts/x.md")

        with self.db._connect() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO block_cycles "
                    "(round_id, block, cycle, artifact_path) VALUES (?, ?, ?, ?)",
                    (round_id, "B5", 1, "content/drafts/x.md"),
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO review_receipts "
                    "(cycle_id, reviewer_agent, decision, result_json) VALUES (?, ?, ?, ?)",
                    (999, "revisor", "approved", "{}"),
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO workflow_events "
                    "(round_id, block, event, payload_json) VALUES (?, ?, ?, ?)",
                    (999, "B5", "event", "{}"),
                )

        self.assertIsInstance(cycle_id, int)

    def test_public_workflow_apis_reject_unscoped_completion_and_closed_round(self):
        from content_ops.orchestration import WorkflowBlocked, record_human_completion, start_block_cycle

        artifact = self.path.parent.parent / "artifact.md"
        artifact.write_text("draft", encoding="utf-8")
        round_id = self.db.create_round("Pilar", "round.md")
        with self.assertRaises(ValueError):
            self.db.record_workflow_event(round_id, "B1", "block_completed")
        with self.assertRaises(ValueError):
            self.db.record_block_validation("B1", "artifact.md")
        self.complete_prior_blocks(round_id, ("B1", "B2", "B3", "B4", "B5", "B6"))
        start_block_cycle(self.db, round_id, "B7", "artifact.md")
        record_human_completion(self.db, round_id, "B7", "artifact.md", "idea-1")
        self.complete_prior_blocks(round_id, ("B8", "B10", "B9", "B11"))
        self.db.close_round(round_id)
        with self.assertRaises(WorkflowBlocked):
            self.db.record_review_result(
                1,
                "revisor",
                "feedback",
                '{"decision":"feedback","artifact":"artifact.md","feedback":[],"checks":[{"name":"quality","status":"pass","evidence":"ok"}]}',
            )

    def test_latest_block_state_returns_latest_event(self):
        round_id = self.db.create_round("Pilar", "runtime/rodadas/1.md")
        self.assertIsNone(self.db.latest_block_state(round_id, "B5"))
        with self.assertRaises(ValueError):
            self.db.record_workflow_event(round_id, "B5", "cycle_started")
        self.assertIsNone(self.db.latest_block_state(round_id, "B5"))

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

    def test_approved_post_can_transition_to_published(self):
        from content_ops.models import PostStatus

        post_id = self.db.create_post(PostStatus.APPROVED, "Aprovado")
        self.db.transition_post(post_id, PostStatus.PUBLISHED)

        with sqlite3.connect(self.path) as connection:
            status = connection.execute(
                "SELECT status FROM posts WHERE id = ?", (post_id,)
            ).fetchone()[0]
        self.assertEqual(status, "published")

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

        with self.assertRaises(ValueError):
            self.db.close_round(round_id)
        self.assertEqual(self.db.list_rounds()[0]["status"], "open")

    def test_close_round_requires_all_blocks_and_human_b7_completion(self):
        from content_ops.orchestration import record_human_completion

        round_id = self.db.create_round("Pilar", "round.md")
        self.complete_prior_blocks(round_id, ("B1", "B2", "B3", "B4", "B5", "B6"))
        self.db.start_block_cycle(round_id, "B7", "content/drafts/x.md")
        with self.assertRaises(ValueError):
            self.db.close_round(round_id)
        record_human_completion(self.db, round_id, "B7", "content/drafts/x.md", "idea-1")
        self.complete_prior_blocks(round_id, ("B8", "B10", "B9", "B11"))
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

    def test_block_validation_records_reviewer_approval(self):
        round_id = self.db.create_round("Pilar", "round.md")
        self.complete_prior_blocks(round_id, ("B1", "B2", "B3"))
        cycle_id = self.db.start_block_cycle(round_id, "B4", "content/drafts/x.md")
        result = '{"decision":"approved","artifact":"content/drafts/x.md","feedback":[],"checks":[{"name":"quality","status":"pass","evidence":"ok"}]}'
        self.db.record_review_result(cycle_id, "revisor", "approved", result)
        self.db.record_block_validation("B4", "content/drafts/x.md", round_id, 1)

        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT block, artifact_path, approved FROM block_validations WHERE block = ?",
                ("B4",),
            ).fetchone()
        self.assertEqual(row[0], "B4")
        self.assertEqual(row[1], "content/drafts/x.md")
        self.assertEqual(row[2], 1)

    def test_block_validation_rolls_back_completion_when_compatibility_insert_fails(self):
        round_id = self.db.create_round("Pilar", "round.md")
        self.complete_prior_blocks(round_id, ("B1", "B2", "B3"))
        cycle_id = self.db.start_block_cycle(round_id, "B4", "content/drafts/x.md")
        result = '{"decision":"approved","artifact":"content/drafts/x.md","feedback":[],"checks":[{"name":"quality","status":"pass","evidence":"ok"}]}'
        self.db.record_review_result(cycle_id, "revisor", "approved", result)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                CREATE TRIGGER reject_compatibility_validation
                BEFORE INSERT ON block_validations
                WHEN NEW.block = 'B4'
                BEGIN
                    SELECT RAISE(ABORT, 'compatibility insert failed');
                END
                """
            )

        with self.assertRaises(sqlite3.IntegrityError):
            self.db.record_block_validation("B4", "content/drafts/x.md", round_id, 1)

        with sqlite3.connect(self.path) as connection:
            self.assertIsNone(connection.execute(
                "SELECT 1 FROM workflow_events WHERE round_id = ? AND block = ? AND event = 'block_completed'",
                (round_id, "B4"),
            ).fetchone())
            self.assertIsNone(connection.execute(
                "SELECT 1 FROM block_validations WHERE block = ?",
                ("B4",),
            ).fetchone())

    def test_create_idea_stores_multi_research_sources(self):
        self.db.create_research_report("IA", "research/ia.md", pillar="IA aplicada")
        self.db.upsert_pillar("IA aplicada")
        self.db.approve_pillar("IA aplicada")
        import json

        idea_id = self.db.create_idea(
            "Ideia cruzada",
            "IA aplicada",
            "research/ia.md",
            sources=["research/ia.md", "research/ia2.md"],
        )

        with sqlite3.connect(self.path) as connection:
            sources = connection.execute(
                "SELECT sources FROM ideas WHERE id = ?", (idea_id,)
            ).fetchone()[0]
        self.assertEqual(json.loads(sources), ["research/ia.md", "research/ia2.md"])


if __name__ == "__main__":
    unittest.main()
