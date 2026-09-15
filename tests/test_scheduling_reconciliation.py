from datetime import datetime
from pathlib import Path

import pytest

from scheduling_reconciliation import cli_reconcile, reconcile_local_state


def make_content(tmp_path: Path) -> Path:
    content = tmp_path / "content"
    for folder in ("drafts", "published", "approved", "arquived"):
        (content / folder).mkdir(parents=True)
    return content


def test_reconcile_detects_published_file_without_publication_marker(tmp_path):
    content = make_content(tmp_path)
    post = content / "published" / "post.md"
    post.write_text("Texto\n\n## Fontes\n- Fonte\n")
    result = reconcile_local_state(content, now=datetime(2026, 9, 16, 10))
    assert result["problems"][0]["type"] == "published_without_publication_marker"
    assert result["problems"][0]["topic_id"] == "post"
    assert result["safe_actions_only"] is True


def test_reconcile_detects_draft_with_agendado_marker(tmp_path):
    content = make_content(tmp_path)
    post = content / "drafts" / "post.md"
    post.write_text("Texto\n<!-- agendado: 2026-09-20T10:00 America/Sao_Paulo -->\n\n## Fontes\n- Fonte\n")
    result = reconcile_local_state(content)
    assert result["problems"][0]["type"] == "draft_with_agendado_marker"
    assert result["problems"][0]["topic_id"] == "post"


def test_reconcile_accepts_published_post_with_both_markers(tmp_path):
    content = make_content(tmp_path)
    post = content / "published" / "post.md"
    post.write_text(
        "Texto\n"
        "<!-- agendado: 2026-09-20T10:00 America/Sao_Paulo -->\n"
        "<!-- publicado: 2026-09-20T10:00 America/Sao_Paulo -->\n\n"
        "## Fontes\n- Fonte\n"
    )
    result = reconcile_local_state(content, now=datetime(2026, 9, 21, 10))
    assert result["problems"] == []


def test_reconcile_accepts_scheduled_post_before_publication(tmp_path):
    content = make_content(tmp_path)
    post = content / "published" / "post.md"
    post.write_text(
        "Texto\n"
        "<!-- agendado: 2026-09-20T10:00 America/Sao_Paulo -->\n\n"
        "## Fontes\n- Fonte\n",
        encoding="utf-8",
    )
    result = reconcile_local_state(content, now=datetime(2026, 9, 16, 10))
    assert result["problems"] == []


def test_reconcile_reports_mismatched_topic_status(tmp_path):
    content = make_content(tmp_path)
    topic_file = tmp_path / "topics.yaml"
    topic_file.write_text(
        "topics:\n  topic_20260915_01:\n    status: published\n",
        encoding="utf-8",
    )
    post = content / "drafts" / "topic_20260915_01.md"
    post.write_text("Texto\n\n## Fontes\n- Fonte\n")
    result = reconcile_local_state(content, topic_files=[topic_file])
    assert any(p["type"] == "topic_status_mismatch" for p in result["problems"])


def test_reconcile_reports_nonempty_approved_folder_but_accepts_scheduled_post(tmp_path):
    content = make_content(tmp_path)
    (content / "approved" / "orphan.md").write_text("Texto\n\n## Fontes\n- Fonte\n")
    post = content / "published" / "orphan.md"
    post.write_text("Texto\n<!-- agendado: 2026-09-20T10:00 America/Sao_Paulo -->\n\n## Fontes\n- Fonte\n")
    result = reconcile_local_state(content)
    assert result["problems"][0]["type"] == "approved_folder_not_empty"
    assert not any(p["type"] == "published_without_publication_marker" for p in result["problems"])


def test_cli_reconcile_persists_yaml(tmp_path, capsys):
    content = make_content(tmp_path)
    post = content / "published" / "post.md"
    post.write_text("Texto\n\n## Fontes\n- Fonte\n")
    output = tmp_path / "report.yaml"
    code = cli_reconcile(
        ["--content", str(content), "--output", str(output)],
        now="2026-09-16T10:00:00-03:00",
        topic_files=[],
    )
    assert code == 1
    assert output.is_file()
    assert "published_without_publication_marker" in output.read_text()
