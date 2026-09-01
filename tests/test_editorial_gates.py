from pathlib import Path


def test_research_and_write_contracts_require_quality_gates():
    research = Path(".agents/skills/research-topic/SKILL.md").read_text()
    write = Path(".agents/skills/write-post/SKILL.md").read_text()

    assert "duas fontes independentes" in research
    assert "conexão" in research
    assert "9/10" in write
    assert "escrita-humana" in write
