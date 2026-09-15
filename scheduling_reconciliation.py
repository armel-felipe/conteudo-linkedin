#!/usr/bin/env python3
"""Reconcile local editorial state without making silent repairs."""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent
AGENDADO_RE = re.compile(r"<!--\s*agendado:[^>]*-->", re.IGNORECASE)
PUBLICADO_RE = re.compile(r"<!--\s*publicado:[^>]*-->", re.IGNORECASE)
EXPECTED_STATUS = {"drafts": "drafted", "published": "published", "arquived": "archived"}


def _load_topic_files(paths: list[Path]) -> dict[str, tuple[Path, dict[str, Any]]]:
    topics_by_id: dict[str, tuple[Path, dict[str, Any]]] = {}
    for raw in paths:
        path = Path(raw)
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        topics = payload.get("topics", {})
        if isinstance(topics, list):
            items = {item.get("id"): item for item in topics if isinstance(item, dict)}
        else:
            items = {topic_id: topic for topic_id, topic in topics.items() if isinstance(topic, dict)}
        for topic_id, item in items.items():
            topics_by_id.setdefault(topic_id, (path, item))
    return topics_by_id


def reconcile_local_state(
    content_dir: str | Path,
    *,
    topic_files: list[str | Path] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    content = Path(content_dir)
    problems: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    files: dict[str, list[Path]] = {folder: [] for folder in ("drafts", "published", "approved", "arquived")}

    for folder, file_list in files.items():
        directory = content / folder
        if not directory.exists():
            continue
        if folder == "approved" and any(directory.iterdir()):
            problems.append({"type": "approved_folder_not_empty", "folder": folder})
        file_list.extend(sorted(directory.glob("*.md")))

    for folder in ("drafts", "published", "arquived"):
        for post in files[folder]:
            text = post.read_text(encoding="utf-8")
            topic_id = post.stem
            scheduled = bool(AGENDADO_RE.search(text))
            published = bool(PUBLICADO_RE.search(text))
            if folder == "drafts" and scheduled:
                problems.append({"type": "draft_with_agendado_marker", "topic_id": topic_id, "file": str(post)})
            if folder == "published" and not (published or scheduled):
                problems.append({"type": "published_without_publication_marker", "topic_id": topic_id, "file": str(post)})
            if folder == "arquived" and (scheduled or published):
                problems.append({"type": "archived_with_active_markers", "topic_id": topic_id, "file": str(post)})

    topics_by_id = _load_topic_files(topic_files or [])
    if topics_by_id:
        for folder in ("drafts", "published"):
            for post in files[folder]:
                topic_id = post.stem
                if topic_id not in topics_by_id:
                    problems.append({"type": "topic_file_missing", "topic_id": topic_id, "file": str(post)})
                    continue
                path, payload = topics_by_id[topic_id]
                expected = EXPECTED_STATUS[folder]
                actual = payload.get("status")
                if actual != expected:
                    problems.append({
                        "type": "topic_status_mismatch",
                        "topic_id": topic_id,
                        "file": str(post),
                        "topic_file": str(path),
                        "expected": expected,
                        "actual": actual,
                    })
                    actions.append({
                        "type": "set_topic_status",
                        "topic_id": topic_id,
                        "from": actual,
                        "to": expected,
                        "safe": True,
                    })

    return {
        "generated_at": (now or datetime.now().astimezone()).isoformat(timespec="seconds"),
        "content": str(content),
        "problems": problems,
        "actions": actions,
        "safe_actions_only": all(action.get("safe") for action in actions),
    }


def cli_reconcile(
    argv: list[str] | None = None,
    *,
    now: str | None = None,
    topic_files: list[Path] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content", default=str(ROOT / "content"))
    parser.add_argument("--topics", action="append", default=[])
    parser.add_argument("--output", default=str(ROOT / "runs" / "scheduling-reconciliation.yaml"))
    args = parser.parse_args(argv)
    topics = topic_files or [Path(ROOT, "research", "topics") / name for name in args.topics]
    observed = datetime.fromisoformat(now) if now else None
    report = reconcile_local_state(args.content, topic_files=topics, now=observed)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(report, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"Problems: {len(report['problems'])}")
    print(f"Report: {output}")
    return 1 if report["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(cli_reconcile())
