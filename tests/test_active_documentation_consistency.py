from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]

ACTIVE_DOCS = [
    ROOT / "AGENTS.md",
    ROOT / "README.md",
    ROOT / "mapa.md",
    ROOT / "docs" / "roadmap.md",
    ROOT / "docs" / "browser-route-contract.md",
    ROOT / "docs" / "fluxo-operacao.md",
    ROOT / ".agents" / "skills" / "qa-draft" / "SKILL.md",
    ROOT / ".agents" / "skills" / "publicar-linkedin" / "SKILL.md",
    ROOT / ".agents" / "skills" / "orquestrador-runtime" / "SKILL.md",
]


@pytest.mark.parametrize("path", ACTIVE_DOCS)
def test_active_docs_do_not_route_publication_through_approved_folder(path):
    text = path.read_text(encoding="utf-8")
    forbidden = (
        "publica content/approved/",
        "publicar fora de approved/",
        "somente de content/approved/",
        "publicar conteúdo fora de content/approved/",
    )
    assert not any(fragment in text for fragment in forbidden), path


@pytest.mark.parametrize("path", ACTIVE_DOCS)
def test_active_docs_keep_approval_separate_from_browser_mutation(path):
    text = path.read_text(encoding="utf-8").lower()
    forbidden = (
        "aprovar é a decisão de agendar",
        "aprovar (= decidir agendar)",
        "aprovar é decisão exclusiva do humano e dispara",
        "aprovação ... dispara o agendamento",
    )
    assert not any(fragment in text for fragment in forbidden), path


def test_active_browser_contract_names_visual_first_route_and_read_only_fallback():
    text = (ROOT / "docs" / "browser-route-contract.md").read_text(encoding="utf-8").lower()
    assert "cua embedded browser" in text
    assert "browser_native" in text
    assert "read-only" in text


def test_topic_yaml_files_are_parseable():
    topic_files = sorted((ROOT / "research" / "topics").glob("topics_*.yaml"))
    assert topic_files
    for path in topic_files:
        with path.open(encoding="utf-8") as handle:
            assert yaml.safe_load(handle) is not None, path
