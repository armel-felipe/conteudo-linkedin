from pathlib import Path
import json
import re

from gauntlet_loop import run_gauntlet, validate_review


ROOT = Path(__file__).parents[1]
NORMATIVE_CRITERIA = (
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
)


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
    assert tuple(criteria) == NORMATIVE_CRITERIA


def review(criteria=None, **overrides):
    payload = {
        "decision": "approved",
        "coverage": 1.0,
        "criteria": {name: 10 for name in NORMATIVE_CRITERIA} if criteria is None else criteria,
        "hard_failures": [],
        "feedback": [],
        "artifact": "content/drafts/topic.md",
    }
    payload.update(overrides)
    return payload


def test_validate_review_accepts_the_complete_normative_criteria_set():
    result = validate_review(review())
    assert result["valid"] is True
    assert result["quality_feedback"] == []


def test_validate_review_rejects_omitted_normative_criterion():
    criteria = {name: 10 for name in NORMATIVE_CRITERIA[:-1]}
    result = validate_review(review(criteria))
    assert result["valid"] is False
    assert result["terminal"] is True


def test_validate_review_rejects_extra_normative_criterion():
    criteria = {name: 10 for name in NORMATIVE_CRITERIA} | {"clareza_extra": 10}
    result = validate_review(review(criteria))
    assert result["valid"] is False
    assert result["terminal"] is True


def test_hard_failure_blocks_a_high_coverage_complete_review(tmp_path):
    artifact = "draft.md"
    (tmp_path / artifact).write_text("draft")

    result = run_gauntlet(
        lambda feedback: artifact,
        lambda artifact, feedback: review(
            artifact=artifact,
            hard_failures=["unsupported claim"],
        ),
        artifact_path=artifact,
        workspace_root=tmp_path,
    )

    assert result["status"] == "blocked"
    assert result["cycle_count"] == 1


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
