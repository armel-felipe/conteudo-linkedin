from pathlib import Path

from diversity import (
    concentration_report,
    load_exploratory_questions,
    normalize_diversity,
    topic_distance,
)


ROOT = Path(__file__).resolve().parents[1]


def test_normalize_diversity_fills_unknown_dimensions():
    assert normalize_diversity({"mechanism": ["custo"]}) == {
        "context": ["unknown"],
        "mechanism": ["custo"],
        "actor": ["unknown"],
        "change_type": ["unknown"],
    }


def test_distance_penalizes_same_mechanism_and_context():
    candidate = {"id": "new", "diversity": {
        "context": ["varejo"], "mechanism": ["custo"],
        "actor": ["gestor"], "change_type": ["adocao"],
    }}
    recent = [{"id": "old", "diversity": {
        "context": ["varejo"], "mechanism": ["custo"],
        "actor": ["cliente"], "change_type": ["falha"],
    }}]
    result = topic_distance(candidate, recent)
    assert result["distance_from_recent_topics"] < 5
    assert result["closest_topics"] == ["old"]


def test_distance_rewards_two_changed_dimensions():
    candidate = {"id": "new", "diversity": {
        "context": ["educacao"], "mechanism": ["autoridade"],
        "actor": ["regulador"], "change_type": ["conflito"],
    }}
    recent = [{"id": "old", "diversity": {
        "context": ["varejo"], "mechanism": ["custo"],
        "actor": ["gestor"], "change_type": ["adocao"],
    }}]
    assert topic_distance(candidate, recent)["distance_from_recent_topics"] >= 8


def test_concentration_report_counts_mechanisms_and_unknowns():
    report = concentration_report([
        {"diversity": {"context": ["varejo"], "mechanism": ["custo"],
                        "actor": ["gestor"], "change_type": ["falha"]}},
        {"diversity": {"context": ["varejo"], "mechanism": ["custo"],
                        "actor": ["gestor"], "change_type": ["falha"]}},
        {"diversity": {"context": ["varejo"], "mechanism": ["confianca"],
                        "actor": ["cliente"], "change_type": ["comportamento"]}},
    ])
    assert report["by_mechanism"] == {"confianca": 1, "custo": 2}
    assert report["unknown_count"] == 0


def test_each_front_has_exploratory_questions():
    questions = load_exploratory_questions(ROOT / "config/frentes.yaml")
    assert questions
    assert all(len(items) >= 4 for items in questions.values())
    assert all(all(item.endswith("?") for item in items) for items in questions.values())
