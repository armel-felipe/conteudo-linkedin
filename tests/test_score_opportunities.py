import hashlib
from pathlib import Path

import pytest
import yaml

from score_opportunities import load_scoring_config, run_scoring, score_topic, score_topics


ROOT = Path(__file__).resolve().parents[1]
SCORING_CONFIG_SHA256 = "4db37649eef7ce7e1e29cfd18db9e3e8d471b337173308eb4ec3ddbe7b9f08ef"


def load_yaml(relative_path: str):
    return yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))


def test_scores_topic_from_configured_weights():
    topic = {"id": "topic_a", "scores": {"freshness": 8, "relevance": 10}}
    weights = {"freshness": 0.5, "relevance": 0.5}
    result = score_topic(topic, weights)
    assert result["scores"]["total"] == 90.0


def test_rejects_missing_or_out_of_range_criteria():
    with pytest.raises(ValueError, match="criteria"):
        score_topic(
            {"id": "topic_a", "scores": {"freshness": 11}},
            {"freshness": 1.0},
        )


def test_rejects_weights_that_do_not_sum_to_one(tmp_path):
    config = tmp_path / "scoring.yaml"
    config.write_text("weights:\n  freshness: 0.5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="weights"):
        load_scoring_config(config)


def test_empty_topics_produce_empty_output():
    assert score_topics([], {"freshness": 1.0}) == []


def test_scoring_adds_distance_when_history_is_supplied():
    topic = {"id": "new", "diversity": {
        "context": ["educacao"], "mechanism": ["autoridade"],
        "actor": ["regulador"], "change_type": ["conflito"],
    }, "scores": {
        "freshness": 8, "relevance": 8, "debate": 8, "evidence": 8,
        "author_fit": 8, "originality": 8, "linkedin_fit": 8,
        "distance_from_recent_topics": 0,
    }}
    result = score_topics(
        [topic],
        load_scoring_config(ROOT / "config/scoring.yaml"),
        recent_topics=[{"id": "old", "diversity": {
            "context": ["varejo"], "mechanism": ["custo"],
            "actor": ["gestor"], "change_type": ["adocao"],
        }}],
    )
    assert result[0]["scores"]["distance_from_recent_topics"] >= 8
    assert result[0]["diversity_score"]["closest_topics"] == ["old"]


def test_legacy_scoring_without_history_uses_neutral_distance():
    topic = {"id": "legacy", "scores": {
        "freshness": 8, "relevance": 8, "debate": 8, "evidence": 8,
        "author_fit": 8, "originality": 8, "linkedin_fit": 8,
    }}
    result = score_topics(
        [topic], load_scoring_config(ROOT / "config/scoring.yaml")
    )
    assert result[0]["scores"]["distance_from_recent_topics"] == 0
    assert "diversity_score" not in result[0]


def test_cli_accepts_recent_topics_for_diversity_scoring(tmp_path):
    import score_opportunities

    input_path = tmp_path / "topics.yaml"
    recent_path = tmp_path / "recent.yaml"
    output_path = tmp_path / "scored.yaml"
    base_scores = {
        "freshness": 8, "relevance": 8, "debate": 8, "evidence": 8,
        "author_fit": 8, "originality": 8, "linkedin_fit": 8,
        "distance_from_recent_topics": 0,
    }
    input_path.write_text(yaml.safe_dump({"topics": [{
        "id": "new", "scores": base_scores,
        "diversity": {"context": ["educacao"], "mechanism": ["autoridade"],
                       "actor": ["regulador"], "change_type": ["conflito"]},
    }]}), encoding="utf-8")
    recent_path.write_text(yaml.safe_dump({"topics": [{
        "id": "old", "diversity": {"context": ["varejo"], "mechanism": ["custo"],
                                       "actor": ["gestor"], "change_type": ["adocao"]},
    }]}), encoding="utf-8")
    assert score_opportunities.main([
        "--input", str(input_path), "--config", str(ROOT / "config/scoring.yaml"),
        "--output", str(output_path), "--recent-topics", str(recent_path),
    ]) == 0
    scored = yaml.safe_load(output_path.read_text(encoding="utf-8"))["topics"][0]
    assert scored["diversity_score"]["closest_topics"] == ["old"]


@pytest.mark.parametrize(
    "weights",
    [
        {"freshness": 1.0},
        {"freshness": -0.1, "relevance": 1.1},
        {"freshness": "0.5", "relevance": 0.5},
        {"freshness": 0.4, "relevance": 0.5},
    ],
    ids=["different-criteria", "negative-value", "non-numeric-value", "wrong-sum"],
)
def test_run_scoring_rejects_invalid_weight_maps(weights):
    topics = [{"id": "topic_a", "scores": {"freshness": 8, "relevance": 10}}]

    with pytest.raises(ValueError, match="weights"):
        run_scoring(topics, weights)


def test_parallel_scoring_uses_same_topics_and_reports_movements():
    report = load_yaml("research/audits/scoring-parallel-2026-09-06.yaml")
    topics = load_yaml(report["method"]["sample_path"])["topics"]
    config_path = ROOT / "config/scoring.yaml"
    current_weights = load_scoring_config(config_path)
    alternative_weights = report["alternative_weights"]

    assert report["same_sample"] is True
    assert [topic["id"] for topic in topics] == report["method"]["sample_topic_ids"]
    assert report["current_weights"] == current_weights
    assert hashlib.sha256(config_path.read_bytes()).hexdigest() == SCORING_CONFIG_SHA256
    sample_path = ROOT / report["method"]["sample_path"]
    sample_fingerprint = f"sha256:{hashlib.sha256(sample_path.read_bytes()).hexdigest()}"
    assert report["sample_fingerprint"] == sample_fingerprint

    current = run_scoring(topics, current_weights)
    alternative = run_scoring(topics, alternative_weights)
    current_ranking = [
        {"rank": rank, "id": topic["id"], "score": topic["scores"]["total"]}
        for rank, topic in enumerate(current, start=1)
    ]
    alternative_ranking = [
        {"rank": rank, "id": topic["id"], "score": topic["scores"]["total"]}
        for rank, topic in enumerate(alternative, start=1)
    ]
    assert report["current_ranking"] == current_ranking
    assert report["alternative_ranking"] == alternative_ranking

    current_by_id = {item["id"]: item for item in current_ranking}
    alternative_by_id = {item["id"]: item for item in alternative_ranking}
    expected_movements = []
    topics_by_id = {topic["id"]: topic for topic in topics}
    for current_item in current_ranking:
        topic = topics_by_id[current_item["id"]]
        topic_id = topic["id"]
        deltas = {}
        for criterion in current_weights:
            deltas[criterion] = (
                alternative_weights[criterion] - current_weights[criterion]
            ) * topic["scores"][criterion]
        positive = [
            criterion
            for criterion, delta in sorted(
                deltas.items(), key=lambda item: -item[1]
            )
            if delta > 0
        ]
        negative = [
            criterion
            for criterion, delta in sorted(
                deltas.items(), key=lambda item: item[1]
            )
            if delta < 0
        ]
        expected_movements.append(
            {
                "id": topic_id,
                "current_rank": current_by_id[topic_id]["rank"],
                "alternative_rank": alternative_by_id[topic_id]["rank"],
                "rank_delta": (
                    current_by_id[topic_id]["rank"]
                    - alternative_by_id[topic_id]["rank"]
                ),
                "score_delta": round(
                    alternative_by_id[topic_id]["score"]
                    - current_by_id[topic_id]["score"],
                    2,
                ),
                "causing_criteria": {"positive": positive, "negative": negative},
            }
        )
    assert report["movements"] == expected_movements
    assert report["method"]["rank_delta_convention"] == "current_rank - alternative_rank"
    assert report["recommendation"] == "inconclusive"
    recommendation_reason = report["recommendation_reason"]
    assert isinstance(recommendation_reason, str) and recommendation_reason.strip()
    reason = recommendation_reason.casefold()
    assert any(
        phrase in reason
        for phrase in ("amostra é pequena", "amostra e pequena", "amostra pequena")
    )
    assert any(
        phrase in reason
        for phrase in ("não há métricas", "nao ha metricas", "author_fit")
    )
