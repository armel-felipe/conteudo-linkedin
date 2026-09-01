"""Small, reusable contracts for selecting and checkpointing editorial batches."""

import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml


CANONICAL_STAGES = [
    "research-topic",
    "brief_review_gauntlet",
    "write-post",
    "critique-post",
    "correction_gauntlet",
    "humanize_pass_1",
    "humanize_review_1",
    "humanize_pass_2",
    "humanize_review_2",
    "approval_humana",
]
PERSISTENCE_ORDER = ["artifact", "result", "state.yaml", "event", "manifest"]


def _atomic_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as handle:
        yaml.safe_dump(value, handle, sort_keys=False)
        temporary = handle.name
    os.replace(temporary, path)


def _topics_from_files(topics_dir):
    topics = {}
    for path in sorted(Path(topics_dir).glob("topics_*.yaml")):
        document = yaml.safe_load(path.read_text()) or {}
        for topic in document.get("topics", []):
            topics[topic["topic_id"]] = topic
    return topics


def load_and_select_topics(backlog_path, topics_dir, selection):
    topics = _topics_from_files(topics_dir)
    backlog_ids = re.findall(r"topic_[A-Za-z0-9_]+", Path(backlog_path).read_text())
    eligible = {
        topic_id: topics[topic_id]
        for topic_id in backlog_ids
        if topic_id in topics and topics[topic_id].get("status") == "ready_for_research"
    }

    if selection == "all":
        chosen_ids = sorted(eligible, key=lambda topic_id: (-eligible[topic_id]["score"], topic_id))
    elif selection.isdigit():
        count = int(selection)
        ordered = sorted(eligible, key=lambda topic_id: (-eligible[topic_id]["score"], topic_id))
        chosen_ids = ordered[:count]
    else:
        chosen_ids = [topic_id.strip() for topic_id in selection.split(",") if topic_id.strip()]
        invalid = [
            topic_id
            for topic_id in chosen_ids
            if topic_id not in eligible
        ]
        if invalid:
            raise ValueError(f"invalid or non-ready topic ids: {', '.join(invalid)}")

    return [dict(eligible[topic_id]) for topic_id in chosen_ids]


def freeze_manifest(runs_dir, run_id, selection, topics):
    path = Path(runs_dir) / run_id / "manifest.yaml"
    if path.exists():
        manifest = yaml.safe_load(path.read_text())
        if not manifest.get("queue_frozen"):
            raise ValueError("existing manifest is not frozen")
        return manifest

    manifest = {
        "contract_version": "1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selection": selection,
        "queue_frozen": True,
        "queue": [
            {
                "topic_id": topic["topic_id"],
                "position": position,
                "status": "queued",
                "current_stage": "research-topic",
                "score": topic["score"],
            }
            for position, topic in enumerate(topics, start=1)
        ],
        "topics": {},
    }
    _atomic_write(path, manifest)
    return manifest


def checkpoint_valid(state, workspace_root):
    checkpoint = state.get("checkpoint", {})
    if not state.get("run_id") or not state.get("topic_id"):
        return False
    if not checkpoint.get("result") or not checkpoint.get("last_artifact"):
        return False
    if not checkpoint.get("input_fingerprint", "").startswith("sha256:"):
        return False
    if not checkpoint.get("saved_at") or checkpoint.get("stage") not in state.get("completed_stages", []):
        return False
    root = Path(workspace_root).resolve()
    paths = [checkpoint["last_artifact"], *checkpoint.get("paths", [])]
    for relative_path in paths:
        candidate = (root / relative_path).resolve()
        if root not in candidate.parents or not candidate.is_file():
            return False
    return True


def resume_stage(state):
    completed = set(state.get("completed_stages", []))
    return next(stage for stage in CANONICAL_STAGES if stage not in completed)


def idempotency_key(run_id, topic_id, stage, cycle):
    return run_id, topic_id, stage, cycle


def continue_after_failure(queue, topic_id, error):
    item = next(item for item in queue if item["topic_id"] == topic_id)
    item.update(status="blocked", error=error)
    return [item["topic_id"] for item in queue if item["status"] == "queued"]


def event_path(runs_dir, run_id):
    return Path(runs_dir) / run_id / "events.yaml"


def state_path(runs_dir, run_id, topic_id):
    return Path(runs_dir) / run_id / "topics" / topic_id / "state.yaml"


def review_path(runs_dir, run_id, topic_id, cycle):
    return Path(runs_dir) / run_id / "topics" / topic_id / "reviews" / f"cycle-{cycle:02d}.yaml"
