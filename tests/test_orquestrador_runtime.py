"""Structural validation for the orchestrator runtime (Plano 2)."""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

BLOCKS: dict[str, str] = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
    "B3": "pesquisa-mece",
    "B4": "pesquisa",
    "B5": "cruzamento",
    "B6": "ideacao",
    "B8": "escrita",
    "B10": "escrita-humana",
    "B11": "publicar-linkedin",
}

TASK3_BLOCKS = {
    "B1": "orquestrador-runtime",
    "B2": "pilar",
    "B3": "pesquisa-mece",
    "B4": "pesquisa",
    "B5": "cruzamento",
}

APPROVAL_KEYS = [
    "APPROVAL_PILAR",
    "APPROVAL_PESQUISA",
    "APPROVAL_EXECUCAO",
    "APPROVAL_CRUZAMENTO",
    "APPROVAL_IDEACAO",
    "APPROVAL_ESCRITA",
    "APPROVAL_REFINAMENTO",
    "APPROVAL_VALIDACAO",
    "APPROVAL_PUBLICACAO",
]


class OrquestradorRuntimeStructureTests(unittest.TestCase):
    def test_skill_exists(self):
        skill = REPO_ROOT / ".agents" / "skills" / "orquestrador-runtime" / "SKILL.md"
        self.assertTrue(skill.is_file(), "orquestrador-runtime skill missing")

    def test_skill_covers_all_blocks(self):
        skill = (
            REPO_ROOT / ".agents" / "skills" / "orquestrador-runtime" / "SKILL.md"
        ).read_text(encoding="utf-8")
        for block in BLOCKS:
            self.assertIn(block, skill, f"skill does not mention {block}")

    def test_each_block_has_executor_and_revisor(self):
        for block, slug in BLOCKS.items():
            executor = REPO_ROOT / ".agents" / "agents" / f"{slug}-executor" / "AGENT.md"
            revisor = REPO_ROOT / ".agents" / "agents" / f"{slug}-revisor" / "AGENT.md"
            self.assertTrue(executor.is_file(), f"{block} executor missing")
            self.assertTrue(revisor.is_file(), f"{block} revisor missing")

    def test_reviewers_have_memory(self):
        for block, slug in BLOCKS.items():
            memory = REPO_ROOT / ".agents" / "agents" / f"{slug}-revisor" / "memory.md"
            self.assertTrue(memory.is_file(), f"{block} revisor memory missing")

    def test_agent_files_have_required_sections(self):
        for block, slug in BLOCKS.items():
            for role in ("executor", "revisor"):
                path = REPO_ROOT / ".agents" / "agents" / f"{slug}-{role}" / "AGENT.md"
                content = path.read_text(encoding="utf-8")
                self.assertIn("## Contrato", content, f"{block} {role} missing Contrato")
                self.assertIn("## Processo", content, f"{block} {role} missing Processo")

    def test_env_example_has_all_approval_keys(self):
        env = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
        for key in APPROVAL_KEYS:
            self.assertIn(key, env, f".env.example missing {key}")

    def test_runtime_documents_bounded_explicit_task_protocol(self):
        skill = (REPO_ROOT / ".agents" / "skills" / "orquestrador-runtime" / "SKILL.md").read_text(encoding="utf-8")
        for required in (
            "task",
            "AGENT.md",
            "memory.md",
            "ORCHESTRATOR_MAX_REVIEW_CYCLES",
            "ReviewResult",
            "invalid",
            "workflow-cycle-start",
            "workflow-review",
            "workflow-block-complete",
            "fail-closed",
        ):
            self.assertIn(required, skill, f"runtime protocol missing {required}")

    def test_runtime_documents_feedback_loop_and_limit(self):
        skill = (REPO_ROOT / ".agents" / "skills" / "orquestrador-runtime" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("feedback", skill.lower())
        self.assertIn("3", skill)
        self.assertIn("feedback completo", skill.lower())

    def test_executors_report_structured_artifact_and_cycle(self):
        for slug in TASK3_BLOCKS.values():
            content = (REPO_ROOT / ".agents" / "agents" / f"{slug}-executor" / "AGENT.md").read_text(encoding="utf-8")
            self.assertIn("JSON", content, f"{slug} executor missing JSON output")
            self.assertIn("artifact_path", content, f"{slug} executor missing artifact_path")
            self.assertIn("cycle", content, f"{slug} executor missing cycle")
            self.assertIn('"cycle":1', content, f"{slug} executor example must start at cycle 1")

    def test_final_executors_declare_mandatory_artifact_cycle_json(self):
        for slug in ("escrita", "escrita-humana", "ideacao", "publicar-linkedin"):
            content = (REPO_ROOT / ".agents" / "agents" / f"{slug}-executor" / "AGENT.md").read_text(encoding="utf-8")
            self.assertIn("Retorne somente JSON válido", content)
            self.assertIn('"artifact_path"', content)
            self.assertIn('"cycle"', content)

    def test_reviewers_require_review_result_and_cannot_approve_themselves(self):
        for slug in BLOCKS.values():
            content = (REPO_ROOT / ".agents" / "agents" / f"{slug}-revisor" / "AGENT.md").read_text(encoding="utf-8")
            self.assertIn("ReviewResult", content, f"{slug} reviewer missing ReviewResult")
            for field in ('"decision"', '"artifact"', '"feedback"', '"checks"'):
                self.assertIn(field, content, f"{slug} reviewer missing {field} field")
            self.assertNotIn('"approved"', content, f"{slug} reviewer uses incompatible approved field")
            self.assertIn("não pode editar", content.lower(), f"{slug} reviewer may edit artifacts")
            self.assertIn("registrar sua própria aprovação", content.lower(), f"{slug} reviewer may register approval")

    def test_runtime_describes_review_schema_and_transition_order(self):
        skill = (REPO_ROOT / ".agents" / "skills" / "orquestrador-runtime" / "SKILL.md").read_text(encoding="utf-8")
        for field in ("decision", "artifact", "feedback", "checks"):
            self.assertIn(field, skill)
        self.assertNotIn('"approved"', skill)
        procedure = skill[skill.index("### Procedimento copiável") :]
        self.assertLess(procedure.index("workflow-cycle-start"), procedure.index("workflow-review"))
        self.assertLess(procedure.index("workflow-review"), procedure.index("workflow-block-complete"))

    def test_runtime_text_has_executor_reviewer_completion_flow(self):
        skill = (REPO_ROOT / ".agents" / "skills" / "orquestrador-runtime" / "SKILL.md").read_text(encoding="utf-8")
        procedure = skill[skill.index("### Procedimento copiável") :]
        executor = procedure.index("<slug>-executor/AGENT.md")
        reviewer = procedure.index("<slug>-revisor/AGENT.md")
        self.assertLess(procedure.index("task", executor - 100), reviewer)
        self.assertLess(reviewer, procedure.index("workflow-review"))
        self.assertLess(procedure.index("workflow-review"), procedure.index("workflow-block-complete"))


if __name__ == "__main__":
    unittest.main()
