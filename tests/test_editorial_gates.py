from pathlib import Path
import json
import re


ROOT = Path(__file__).parents[1]


def read_contract(path):
    return (ROOT / path).read_text()


def test_research_and_write_contracts_require_quality_gates():
    research = read_contract(".agents/skills/research-topic/SKILL.md")
    write = read_contract(".agents/skills/write-post/SKILL.md")

    assert "duas fontes independentes" in research
    assert "conexão" in research
    assert "9/10" in write
    assert "escrita-humana" in write


def test_post_uses_exact_normative_criteria_in_order():
    write = read_contract(".agents/skills/write-post/SKILL.md")
    section = re.search(
        r"## Critérios normativos do post\n(.*?)(?=\n## )", write, re.DOTALL
    )
    assert section is not None
    criteria = [
        match.group(2).strip().lower()
        for match in re.finditer(r"^([0-9]+)\. (.+)$", section.group(1), re.MULTILINE)
    ]
    assert criteria == [
        "clareza",
        "força da abertura",
        "originalidade",
        "credibilidade",
        "uso de evidências",
        "risco de alucinação",
        "tom humano",
        "densidade",
        "relevância",
        "consistência com a voz do autor",
        "estrutura obrigatória",
        "pergunta final",
        "tamanho editorial",
        "rastreabilidade das fontes",
    ]


def test_editorial_review_contract_is_structured_and_shared():
    schema = json.loads(read_contract("docs/schemas/gauntlet-review.json"))
    assert schema["required"] == [
        "decision",
        "coverage",
        "criteria",
        "hard_failures",
        "feedback",
        "artifact",
    ]
    assert schema["properties"]["decision"]["enum"] == ["approved", "feedback"]
    assert schema["properties"]["coverage"]["type"] == "number"
    assert schema["properties"]["coverage"]["minimum"] == 0
    assert schema["properties"]["coverage"]["maximum"] == 1
    assert schema["properties"]["hard_failures"]["type"] == "array"
    assert schema["properties"]["feedback"]["type"] == "array"
    for path in (
        ".agents/skills/research-topic/SKILL.md",
        ".agents/skills/write-post/SKILL.md",
    ):
        contract = read_contract(path)
        assert "docs/schemas/gauntlet-review.json" in contract
        assert "hard_failures" in contract


def test_brief_contract_requires_all_research_gates():
    research = read_contract(".agents/skills/research-topic/SKILL.md")
    required = (
        "duas fontes independentes",
        "fonte primária",
        "research questions",
        "conexão explícita com a experiência profissional",
        "seção de limitações",
        "aprovação do Gauntlet",
    )
    assert all(item in research for item in required)


def test_human_writing_requires_two_reviewed_passes_and_hard_failure_gate():
    write = read_contract(".agents/skills/write-post/SKILL.md")
    sequence = "humanize_pass_1 → humanize_review_1 → humanize_pass_2 → humanize_review_2"
    assert sequence in write.replace("`", "")
    assert write.index("humanize_review_1") < write.index("humanize_pass_2")
    assert "hard_failures" in write
    assert "95%" in write
    assert "bloqueiam a aprovação" in write
