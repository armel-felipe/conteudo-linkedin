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
