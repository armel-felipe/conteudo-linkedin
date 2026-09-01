from pathlib import Path


SKILL = Path(".agents/skills/gauntlet-loop/SKILL.md")


def test_gauntlet_defines_five_round_limit_and_hard_gate():
    text = SKILL.read_text()
    assert "5 rodadas" in text
    assert "99%" in text
    assert "9/10" in text
    assert "executor" in text and "revisor" in text


def test_gauntlet_documents_isolated_cycle_and_structured_review_contract():
    text = SKILL.read_text()
    assert "cycle-start" in text
    assert "executor" in text
    assert "deterministic checks" in text
    assert "fresh reviewer" in text
    assert "structured result" in text
    assert "valid JSON" in text
    assert "task" in text


def test_gauntlet_documents_fail_closed_inputs_feedback_and_terminal_block():
    text = SKILL.read_text()
    assert "fail-closed" in text
    assert "missing artifact" in text
    assert "failed validation" in text
    assert "complete feedback" in text
    assert "blocked" in text
    assert "failure reasons" in text
    assert "failed criteria" in text
    assert "last artifact" in text
    assert "cycle count" in text
    assert "caller" in text


def test_quality_gate_returns_feedback_and_retries_instead_of_blocking():
    text = SKILL.read_text().lower()
    assert "coverage <=99%" in text
    assert "criteria <9/10" in text
    assert "feedback" in text
    assert "nao bloqueia" in text
    assert "cada criterio" in text


def test_strict_json_contract_defines_root_types_and_bounds():
    text = SKILL.read_text().lower()
    required_phrases = (
        "objeto raiz",
        "tipos corretos",
        "coverage finito",
        "entre 0 e 1",
        "criteria objeto",
        "numeros 0-10",
        "hard_failures",
        "feedback listas",
        "artifact string nao vazia",
        "decision enum",
    )
    for phrase in required_phrases:
        assert phrase in text


def test_retry_limit_and_terminal_categories_are_explicitly_distinguished():
    text = SKILL.read_text().lower()
    assert "ate 5" in text
    assert "sem sexta rodada" in text
    assert "falha estrutural" in text
    assert "hard failure" in text
    assert "json invalido" in text
    assert "executor/revisor indisponivel" in text
    assert "artifact ausente" in text
    assert "coverage <=99%" in text
    assert "criteria <9/10" in text
