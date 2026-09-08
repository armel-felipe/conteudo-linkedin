import pytest
from pathlib import Path

from scheduling_registry import (
    MARKER_RE,
    _first_line,
    _parse_timestamp,
    find_conflicts,
    scan_posts,
)


ROOT = Path(__file__).resolve().parents[1]


def test_marker_regex_parses_agendado_comment():
    text = "<!-- agendado: 2026-09-10T10:00 America/Sao_Paulo -->"
    assert MARKER_RE.findall(text) == ["2026-09-10T10:00 America/Sao_Paulo"]


def test_first_line_skips_marker_and_blank_lines():
    text = "\n\n<!-- agendado: 2026-09-10T10:00 -->\n\nA conversa sobre IA industrial está crescendo.\n"
    assert _first_line(text) == "A conversa sobre IA industrial está crescendo."


def test_parse_timestamp_handles_brazil_timezone_suffix():
    dt = _parse_timestamp("2026-09-10T10:00 America/Sao_Paulo")
    assert dt is not None
    assert dt.isoformat() == "2026-09-10T10:00:00"


def test_parse_timestamp_returns_none_for_invalid():
    assert _parse_timestamp("not-a-date") is None


def test_scan_posts_finds_published_markers():
    posts = scan_posts()
    # deve encontrar os 3 posts publicados com marker
    published = [p for p in posts if p["folder"] == "published"]
    assert len(published) >= 3
    timestamps = {p["topic_id"]: p["raw_timestamp"] for p in published}
    assert timestamps["topic_20260901_02"] == "2026-09-01T10:00 America/Sao_Paulo"
    assert timestamps["topic_20260901_03"] == "2026-09-08T10:00 America/Sao_Paulo"
    assert timestamps["topic_20260901_04"] == "2026-09-10T10:00 America/Sao_Paulo"


def test_find_conflicts_detects_time_conflict():
    posts = [
        {"topic_id": "a", "timestamp": _parse_timestamp("2026-09-10T10:00 America/Sao_Paulo"), "content_snippet": "x"},
        {"topic_id": "b", "timestamp": _parse_timestamp("2026-09-10T10:00 America/Sao_Paulo"), "content_snippet": "y"},
    ]
    time_conflicts, content_conflicts = find_conflicts(posts)
    assert len(time_conflicts) == 1
    assert time_conflicts[0]["posts"] == ["a", "b"]
    assert content_conflicts == []


def test_find_conflicts_detects_content_conflict():
    posts = [
        {"topic_id": "a", "timestamp": _parse_timestamp("2026-09-10T10:00 America/Sao_Paulo"), "content_snippet": "mesmo texto"},
        {"topic_id": "b", "timestamp": _parse_timestamp("2026-09-11T10:00 America/Sao_Paulo"), "content_snippet": "mesmo texto"},
    ]
    time_conflicts, content_conflicts = find_conflicts(posts)
    assert time_conflicts == []
    assert len(content_conflicts) == 1
    assert content_conflicts[0]["posts"] == ["a", "b"]


def test_find_conflicts_no_conflict_for_distinct_posts():
    posts = [
        {"topic_id": "a", "timestamp": _parse_timestamp("2026-09-10T10:00 America/Sao_Paulo"), "content_snippet": "texto a"},
        {"topic_id": "b", "timestamp": _parse_timestamp("2026-09-11T10:00 America/Sao_Paulo"), "content_snippet": "texto b"},
    ]
    time_conflicts, content_conflicts = find_conflicts(posts)
    assert time_conflicts == []
    assert content_conflicts == []
