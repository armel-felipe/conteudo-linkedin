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


if __name__ == "__main__":
    unittest.main()
