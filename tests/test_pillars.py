import tempfile
import unittest
from pathlib import Path


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


class PillarCommandTests(unittest.TestCase):
    def test_parser_accepts_propose_and_approve_commands(self):
        from content_ops.cli import build_parser

        parser = build_parser()
        self.assertEqual(parser.parse_args(["pillars", "propose"]).pillars_command, "propose")
        approval = parser.parse_args(["pillars", "approve", "Python e dados"])
        self.assertEqual(approval.name, "Python e dados")


if __name__ == "__main__":
    unittest.main()
