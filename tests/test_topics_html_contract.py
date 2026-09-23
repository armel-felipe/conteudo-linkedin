"""Contrato do HTML de temas do Bloco 1.

O `score-opportunities` deve gerar `research/topics/topics_YYYY-MM-DD.html` como
visualização navegável dos temas, versionada junto com os topics. Sem o HTML,
o Bloco 1 não está concluído. Estes testes impedem que o contrato regrida.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Documentos que declaram o contrato do HTML de temas.
CONTRACT_DOCS = [
    ROOT / "AGENTS.md",
    ROOT / "README.md",
    ROOT / "mapa.md",
    ROOT / ".agents" / "skills" / "score-opportunities" / "SKILL.md",
]


@pytest.mark.parametrize("path", CONTRACT_DOCS)
def test_contract_docs_require_topics_html(path):
    text = path.read_text(encoding="utf-8")
    assert "topics_" in text and ".html" in text, path
    assert "obrigat" in text.lower(), path


def test_score_opportunities_skill_defines_html_output_and_flow():
    text = (ROOT / ".agents" / "skills" / "score-opportunities" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    # O HTML aparece como saída obrigatória e como passo do fluxo.
    assert "topics_YYYY-MM-DD.html" in text
    assert "obrigat" in text.lower()
    # O conteúdo mínimo do HTML está especificado.
    for fragment in ("score", "tese", "pergunta central", "sinais", "links"):
        assert fragment in text.lower(), fragment


def test_agents_md_places_html_in_block_1_outputs():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    block_1 = text.split("### Bloco 1")[1].split("### Bloco 2")[0]
    assert "topics_*.html" in block_1
    assert "obrigat" in block_1.lower()


def test_topics_html_is_versioned_not_ignored():
    """O HTML de temas deve ser versionado, não ignorado pelo git."""
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "topics_" not in gitignore
    assert "research/topics" not in gitignore
