from importlib import util
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync_backlog.py"
_spec = util.spec_from_file_location("sync_backlog", SCRIPT)
sync_backlog = util.module_from_spec(_spec)
_spec.loader.exec_module(sync_backlog)


def _root(tmp_path, backlog, topics):
    (tmp_path / "content").mkdir()
    (tmp_path / "research/topics").mkdir(parents=True)
    (tmp_path / "content/backlog.md").write_text(backlog, encoding="utf-8")
    (tmp_path / "research/topics/topics_20260923.yaml").write_text(
        yaml.safe_dump({"topics": topics}), encoding="utf-8"
    )
    return tmp_path


def _backlog(ready_count=2, blocks=("topic_a", "topic_b")):
    lines = [
        "# Content Backlog",
        "",
        "> Temas com `status: ready_for_research`.",
        f"> Leva de 2026-09-23: 12 topics candidatos pontuados; {ready_count} entram no backlog.",
        "",
    ]
    for index, topic_id in enumerate(blocks):
        lines += [f"## 9{index}.00 — Tema {topic_id}", "", topic_id, "", "Status: ready_for_research", ""]
    lines += ["## Fora do backlog", "", "- candidate x", "", "## Como transformar temas em drafts", ""]
    return "\n".join(lines)


TOPICS = [
    {"id": "topic_a", "status": "ready_for_research"},
    {"id": "topic_b", "status": "published"},
]


def test_check_flags_published_topic(tmp_path):
    root = _root(tmp_path, _backlog(), TOPICS)
    assert sync_backlog.sync(write=False, root=root) == 1


def test_write_prunes_published_and_keeps_candidate_section(tmp_path):
    root = _root(tmp_path, _backlog(), TOPICS)
    assert sync_backlog.sync(write=True, root=root) == 0
    text = (root / "content/backlog.md").read_text(encoding="utf-8")

    assert "topic_a" in text
    assert "topic_b" not in text
    assert "Fora do backlog" in text
    assert "Como transformar temas em drafts" in text
    assert "1 entram no backlog" in text
    assert sync_backlog.sync(write=False, root=root) == 0


def test_check_passes_when_preamble_count_is_stale(tmp_path):
    root = _root(tmp_path, _backlog(ready_count=7, blocks=("topic_a",)), TOPICS)
    assert sync_backlog.sync(write=False, root=root) == 1
    assert sync_backlog.sync(write=True, root=root) == 0
    assert "1 entram no backlog" in (root / "content/backlog.md").read_text(encoding="utf-8")
