import pytest

from score_opportunities import load_scoring_config, score_topic, score_topics


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
