from pathlib import Path


COMPACT = Path(".agents/skills/last30days/references/editorial-compact-mode.md")


def test_editorial_compact_mode_is_small_and_preserves_safety_gates():
    text = COMPACT.read_text(encoding="utf-8")
    assert len(text) <= 6000
    for required in ("não inventar", "fonte primária", "incertezas", "não confiável", "cache"):
        assert required in text.lower()


def test_research_topic_points_to_compact_mode():
    text = Path(".agents/skills/research-topic/SKILL.md").read_text(encoding="utf-8")
    assert "editorial-compact-mode.md" in text
