from pathlib import Path

import yaml


def test_today_published_post_has_publication_marker():
    text = Path("content/published/topic_20260914_08.md").read_text(encoding="utf-8")
    assert "<!-- publicado: " in text
    assert "<!-- agendado: 2026-09-15T10:00 America/Sao_Paulo -->" in text


def test_today_published_topic_status_is_published():
    data = yaml.safe_load(Path("research/topics/topics_2026-09-14.yaml").read_text(encoding="utf-8"))
    topics = data["topics"]
    item = next(topic for topic in topics if topic.get("id") == "topic_20260914_08")
    assert item["status"] == "published"
