import tempfile
import threading
import unittest
import sqlite3
from pathlib import Path
from unittest.mock import patch


class PillarProposalTests(unittest.TestCase):
    def test_proposes_ranked_distinct_topics(self):
        from content_ops.pillars import propose_pillars

        proposals = propose_pillars(
            ["Python para dados", "Dados em Python", "Carreira de engenharia"],
            limit=5,
        )

        self.assertEqual(proposals[0].name, "Python e dados")
        self.assertEqual(proposals[0].count, 2)
        self.assertLessEqual(len(proposals), 5)

    def test_records_evidence_ids_and_sorts_ties_alphabetically(self):
        from content_ops.pillars import propose_pillars

        proposals = propose_pillars(
            [("post-2", "Entrevista de emprego"), ("post-1", "LLM para produto")]
        )

        self.assertEqual(
            [proposal.name for proposal in proposals],
            ["Carreira e oportunidades", "IA aplicada"],
        )
        self.assertEqual(proposals[0].evidence_ids, ("post-2",))

    def test_uses_two_frequent_useful_terms_for_unmapped_topics(self):
        from content_ops.pillars import propose_pillars

        proposals = propose_pillars(["Liderança remota", "Liderança de equipes remotas"])

        self.assertEqual(proposals[0].name, "Liderança e remota")

    def test_fallback_ranks_terms_by_their_actual_occurrences(self):
        from content_ops.pillars import propose_pillars

        proposals = propose_pillars([("post-1", "Produto produto produto remoto")])

        self.assertEqual(proposals[0].name, "Produto e remoto")


class PillarPersistenceTests(unittest.TestCase):
    def setUp(self):
        from content_ops.db import Database

        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.database = Database(root / "content.db")
        self.database.initialize()
        self.path = root / "pillars.md"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_writes_proposals_and_approves_a_named_pillar(self):
        from content_ops.pillars import approve_pillar, write_pillar_proposals

        write_pillar_proposals(
            self.path,
            self.database,
            [("linkedin:a", "Python para dados"), ("linkedin:b", "Dados em Python")],
        )
        approve_pillar(self.path, self.database, "Python e dados")

        self.assertTrue(self.database.pillar_is_approved("Python e dados"))
        document = self.path.read_text(encoding="utf-8")
        self.assertIn("# Pilares editoriais", document)
        self.assertIn("evidence_ids: linkedin:a, linkedin:b", document)
        self.assertIn("approved: true", document)

    def test_persists_name_approval_count_and_evidence_ids(self):
        from content_ops.pillars import approve_pillar, write_pillar_proposals

        write_pillar_proposals(
            self.path,
            self.database,
            [("linkedin:a", "Python para dados"), ("linkedin:b", "Dados em Python")],
        )
        approve_pillar(self.path, self.database, "Python e dados")

        pillar = self.database.list_pillars()[0]

        self.assertEqual(pillar.name, "Python e dados")
        self.assertTrue(pillar.approved)
        self.assertEqual(pillar.count, 2)
        self.assertEqual(pillar.evidence_ids, ("linkedin:a", "linkedin:b"))

    def test_approval_only_changes_its_own_section_and_is_idempotent(self):
        from content_ops.pillars import approve_pillar, write_pillar_proposals

        write_pillar_proposals(
            self.path,
            self.database,
            [("linkedin:a", "Python para dados"), ("linkedin:b", "Entrevista de emprego")],
        )

        approve_pillar(self.path, self.database, "Carreira e oportunidades")
        approve_pillar(self.path, self.database, "Carreira e oportunidades")

        self.assertEqual(
            self.path.read_text(encoding="utf-8"),
            "# Pilares editoriais\n\n"
            "Propostas geradas do histórico importado.\n\n"
            "## Carreira e oportunidades\n"
            "count: 1\n"
            "evidence_ids: linkedin:b\n"
            "approved: true\n\n"
            "## Python e dados\n"
            "count: 1\n"
            "evidence_ids: linkedin:a\n"
            "approved: false\n",
        )

    def test_approval_rolls_back_database_when_markdown_write_fails(self):
        from content_ops.pillars import approve_pillar, write_pillar_proposals

        write_pillar_proposals(
            self.path, self.database, [("linkedin:a", "Python para dados")]
        )

        with patch("content_ops.pillars.os.fsync", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                approve_pillar(self.path, self.database, "Python e dados")

        self.assertFalse(self.database.pillar_is_approved("Python e dados"))
        self.assertIn("approved: false", self.path.read_text(encoding="utf-8"))

    def test_approval_preserves_original_when_staging_fsync_fails(self):
        from content_ops.pillars import approve_pillar, write_pillar_proposals

        write_pillar_proposals(
            self.path, self.database, [("linkedin:a", "Python para dados")]
        )
        original = self.path.read_text(encoding="utf-8")

        with patch("content_ops.pillars.os.fsync", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                approve_pillar(self.path, self.database, "Python e dados")

        self.assertFalse(self.database.pillar_is_approved("Python e dados"))
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_approval_restores_markdown_when_directory_fsync_fails_after_replace(self):
        from content_ops.pillars import approve_pillar, write_pillar_proposals

        write_pillar_proposals(
            self.path, self.database, [("linkedin:a", "Python para dados")]
        )
        original = self.path.read_text(encoding="utf-8")

        with patch(
            "content_ops.pillars.os.fsync",
            side_effect=[None, OSError("directory fsync failed"), None, None],
        ):
            with self.assertRaisesRegex(OSError, "directory fsync failed"):
                approve_pillar(self.path, self.database, "Python e dados")

        self.assertFalse(self.database.pillar_is_approved("Python e dados"))
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_approval_restores_markdown_when_database_commit_fails(self):
        from content_ops.pillars import approve_pillar, write_pillar_proposals

        write_pillar_proposals(
            self.path, self.database, [("linkedin:a", "Python para dados")]
        )
        original = self.path.read_text(encoding="utf-8")

        with patch.object(
            self.database, "_commit", side_effect=sqlite3.OperationalError("commit failed")
        ):
            with self.assertRaisesRegex(sqlite3.OperationalError, "commit failed"):
                approve_pillar(self.path, self.database, "Python e dados")

        self.assertFalse(self.database.pillar_is_approved("Python e dados"))
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_reproposal_rolls_back_database_when_markdown_write_fails(self):
        from content_ops.db import Pillar
        from content_ops.pillars import write_pillar_proposals

        write_pillar_proposals(
            self.path, self.database, [("linkedin:a", "Python para dados")]
        )
        before_document = self.path.read_text(encoding="utf-8")

        with patch("content_ops.pillars.os.fsync", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                write_pillar_proposals(
                    self.path, self.database, [("linkedin:b", "LLM para produto")]
                )

        self.assertEqual(
            self.database.list_pillars(),
            [Pillar("Python e dados", False, 1, ("linkedin:a",))],
        )
        self.assertEqual(self.path.read_text(encoding="utf-8"), before_document)

    def test_reproposal_detaches_ideas_from_removed_pillars(self):
        from content_ops.pillars import write_pillar_proposals

        write_pillar_proposals(
            self.path, self.database, [("linkedin:a", "Entrevista de emprego")]
        )
        with self.database._connect() as connection:
            pillar_id = connection.execute(
                "SELECT id FROM pillars WHERE name = ?", ("Carreira e oportunidades",)
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO ideas (title, pillar_id) VALUES (?, ?)", ("Ideia", pillar_id)
            )

        write_pillar_proposals(
            self.path, self.database, [("linkedin:b", "Python para dados")]
        )

        with self.database._connect() as connection:
            self.assertIsNone(connection.execute("SELECT pillar_id FROM ideas").fetchone()[0])
        self.assertEqual([pillar.name for pillar in self.database.list_pillars()], ["Python e dados"])
        self.assertNotIn("Carreira e oportunidades", self.path.read_text(encoding="utf-8"))

    def test_reproposal_replaces_the_pillar_set_and_preserves_matching_approval(self):
        from content_ops.db import Pillar
        from content_ops.pillars import approve_pillar, write_pillar_proposals

        write_pillar_proposals(
            self.path,
            self.database,
            [("linkedin:a", "Python para dados"), ("linkedin:b", "Entrevista de emprego")],
        )
        approve_pillar(self.path, self.database, "Python e dados")
        # Matching names retain approval; an approved name absent from a reproposal
        # is removed because the database mirrors the current editorial record.
        approve_pillar(self.path, self.database, "Carreira e oportunidades")

        write_pillar_proposals(
            self.path,
            self.database,
            [("linkedin:c", "Python para dados"), ("linkedin:d", "LLM para produto")],
        )

        self.assertEqual(
            self.database.list_pillars(),
            [
                Pillar("IA aplicada", False, 1, ("linkedin:d",)),
                Pillar("Python e dados", True, 1, ("linkedin:c",)),
            ],
        )
        document = self.path.read_text(encoding="utf-8")
        self.assertNotIn("Carreira e oportunidades", document)
        self.assertIn("## IA aplicada", document)
        self.assertIn("## Python e dados", document)
        self.assertIn("## Python e dados\ncount: 1\nevidence_ids: linkedin:c\napproved: true", document)

    def test_refuses_a_sixth_approved_pillar(self):
        from content_ops.pillars import approve_pillar

        names = [f"Pilar {number}" for number in range(1, 7)]
        for name in names:
            self.database.upsert_pillar(name)
        self.path.write_text(
            "\n".join(f"## {name}\napproved: false\n" for name in names),
            encoding="utf-8",
        )
        for name in names[:5]:
            approve_pillar(self.path, self.database, name)

        with self.assertRaisesRegex(ValueError, "at most five"):
            approve_pillar(self.path, self.database, names[5])

    def test_concurrent_approvals_preserve_both_markdown_changes(self):
        from content_ops.pillars import approve_pillar, write_pillar_proposals

        write_pillar_proposals(
            self.path,
            self.database,
            [("linkedin:a", "Python para dados"), ("linkedin:b", "Entrevista de emprego")],
        )
        barrier = threading.Barrier(2)
        original_read_bytes = Path.read_bytes
        original_begin = self.database._begin_immediate
        transaction_state = threading.local()
        errors: list[BaseException] = []

        def begin_and_mark_lock(connection: sqlite3.Connection) -> None:
            original_begin(connection)
            transaction_state.holds_write_lock = True

        def read_together(path: Path) -> bytes:
            document = original_read_bytes(path)
            if path == self.path and not getattr(transaction_state, "holds_write_lock", False):
                barrier.wait(timeout=5)
            return document

        def approve(name: str) -> None:
            try:
                approve_pillar(self.path, self.database, name)
            except BaseException as error:
                errors.append(error)

        with patch.object(self.database, "_begin_immediate", side_effect=begin_and_mark_lock):
            with patch(
                "content_ops.pillars.Path.read_bytes", autospec=True, side_effect=read_together
            ):
                threads = [
                    threading.Thread(target=approve, args=("Python e dados",)),
                    threading.Thread(target=approve, args=("Carreira e oportunidades",)),
                ]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=10)

        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.assertTrue(self.database.pillar_is_approved("Python e dados"))
        self.assertTrue(self.database.pillar_is_approved("Carreira e oportunidades"))
        document = self.path.read_text(encoding="utf-8")
        self.assertIn("## Python e dados\ncount: 1\nevidence_ids: linkedin:a\napproved: true", document)
        self.assertIn(
            "## Carreira e oportunidades\ncount: 1\nevidence_ids: linkedin:b\napproved: true",
            document,
        )


class PillarCommandTests(unittest.TestCase):
    def test_parser_accepts_propose_and_approve_commands(self):
        from content_ops.cli import build_parser

        parser = build_parser()
        self.assertEqual(parser.parse_args(["pillars", "propose"]).pillars_command, "propose")
        approval = parser.parse_args(["pillars", "approve", "Python e dados"])
        self.assertEqual(approval.name, "Python e dados")


class ResearchDrivenPillarTests(unittest.TestCase):
    def setUp(self):
        from content_ops.db import Database

        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.database = Database(root / "content.db")
        self.database.initialize()
        self.path = root / "pillars.md"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_proposes_pillars_from_declared_research_pillars(self):
        from content_ops.pillars import propose_pillars_from_research

        self.database.create_research_report(
            "liderança em times de alta performance",
            "research/lideranca-times.md",
            pillar="Liderança e gestão de times",
        )
        self.database.create_research_report(
            "problem solving metodologia mckinsey",
            "research/problem-solving.md",
            pillar="Liderança e gestão de times",
        )
        self.database.create_research_report(
            "ia aplicada a gerentes de negocio",
            "research/ia-gerentes.md",
            pillar="IA aplicada",
        )

        proposals = propose_pillars_from_research(self.database)

        self.assertEqual(
            [proposal.name for proposal in proposals],
            ["Liderança e gestão de times", "IA aplicada"],
        )
        lideranca = next(p for p in proposals if p.name == "Liderança e gestão de times")
        self.assertEqual(lideranca.count, 2)
        self.assertEqual(
            lideranca.evidence_ids,
            ("research/lideranca-times.md", "research/problem-solving.md"),
        )

    def test_fallback_groups_unassigned_research_by_topic_similarity(self):
        from content_ops.pillars import propose_pillars_from_research

        self.database.create_research_report(
            "liderança em times de alta performance", "research/lideranca-times.md"
        )
        self.database.create_research_report(
            "liderança e cultura de equipe", "research/lideranca-cultura.md"
        )
        self.database.create_research_report(
            "problem solving metodologia mckinsey", "research/problem-solving.md"
        )

        proposals = propose_pillars_from_research(self.database)

        self.assertEqual(proposals[0].name, "Liderança")
        self.assertEqual(proposals[0].count, 2)
        self.assertEqual(
            proposals[0].evidence_ids,
            ("research/lideranca-cultura.md", "research/lideranca-times.md"),
        )

    def test_proposes_pillars_ignores_round_and_label_fields(self):
        from content_ops.pillars import propose_pillars_from_research

        round_id = self.database.create_round("Liderança e gestão de times", "runtime/rodadas/x.md")
        self.database.create_research_report(
            "liderança em times de alta performance",
            "research/lideranca-times.md",
            pillar="Liderança e gestão de times",
            round_id=round_id,
            label="2026_08_28 lideranca-gestao-times cultura-times-alta-perf",
        )

        proposals = propose_pillars_from_research(self.database)

        self.assertEqual(proposals[0].name, "Liderança e gestão de times")
        self.assertEqual(proposals[0].evidence_ids, ("research/lideranca-times.md",))

    def test_write_pillar_proposals_from_research_persists_document(self):
        from content_ops.pillars import write_pillar_proposals_from_research

        self.database.create_research_report(
            "liderança em times de alta performance",
            "research/lideranca-times.md",
            pillar="Liderança e gestão de times",
        )

        write_pillar_proposals_from_research(self.path, self.database)

        document = self.path.read_text(encoding="utf-8")
        self.assertIn("## Liderança e gestão de times", document)
        self.assertIn("evidence_ids: research/lideranca-times.md", document)
        self.assertIn("approved: false", document)
        self.assertIn("Propostas derivadas de pesquisas capturadas.", document)


if __name__ == "__main__":
    unittest.main()
