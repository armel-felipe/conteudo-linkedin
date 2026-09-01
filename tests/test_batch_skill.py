from pathlib import Path


def test_batch_skill_documents_selection_and_failure_policy():
    text = Path(".agents/skills/run-editorial-batch/SKILL.md").read_text()
    assert "--topics all" in text
    assert "sequencial" in text
    assert "blocked" in text
    assert "continuar" in text
