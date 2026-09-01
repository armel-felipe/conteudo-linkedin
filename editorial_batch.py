"""Small, reusable contracts for selecting and checkpointing editorial batches."""

import os
import re
import tempfile
from datetime import datetime, timezone
from hashlib import sha256
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


def _atomic_write_bytes(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
        handle.write(value)
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
    if state.get("contract_version") != "1" or not state.get("run_id") or not state.get("topic_id"):
        return False
    if not checkpoint.get("result") or not checkpoint.get("last_artifact"):
        return False
    fingerprint = checkpoint.get("input_fingerprint", "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", fingerprint):
        return False
    if not checkpoint.get("saved_at") or checkpoint.get("stage") not in state.get("completed_stages", []):
        return False
    root = Path(workspace_root).resolve()
    paths = [checkpoint["last_artifact"], *checkpoint.get("paths", [])]
    for relative_path in paths:
        if Path(relative_path).is_absolute():
            return False
        candidate = (root / relative_path).resolve()
        if root not in candidate.parents or not candidate.is_file():
            return False
    artifact_bytes = (root / checkpoint["last_artifact"]).read_bytes()
    if fingerprint != "sha256:" + sha256(artifact_bytes).hexdigest():
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


def persist_stage(
    runs_dir,
    workspace_root,
    run_id,
    topic_id,
    stage,
    cycle,
    artifact_path,
    artifact_content,
    result,
    review,
):
    if stage not in CANONICAL_STAGES:
        raise ValueError(f"unknown stage: {stage}")
    if Path(artifact_path).is_absolute():
        raise ValueError("artifact path must be relative")
    root = Path(workspace_root).resolve()
    artifact = (root / artifact_path).resolve()
    if root not in artifact.parents:
        raise ValueError("artifact path must stay inside workspace")
    manifest_path = Path(runs_dir) / run_id / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    if manifest.get("contract_version") != "1":
        raise ValueError("manifest contract_version must be 1")
    if manifest.get("run_id") != run_id or topic_id not in {item["topic_id"] for item in manifest.get("queue", [])}:
        raise ValueError("manifest ids do not match stage")

    events = event_path(runs_dir, run_id)
    existing = yaml.safe_load(events.read_text()) if events.exists() else {"contract_version": "1", "events": []}
    key = list(idempotency_key(run_id, topic_id, stage, cycle))
    for event in existing["events"]:
        if event["idempotency_key"] == key:
            return yaml.safe_load((Path(runs_dir) / run_id / "manifest.yaml").read_text())

    _atomic_write_bytes(artifact, str(artifact_content).encode())
    result_file = Path(runs_dir) / run_id / "topics" / topic_id / "results" / f"{stage}-cycle-{cycle:02d}.yaml"
    _atomic_write(result_file, result)
    digest = "sha256:" + sha256(artifact.read_bytes()).hexdigest()
    review_file = review_path(runs_dir, run_id, topic_id, cycle)
    result_relative = str(result_file.resolve().relative_to(root))
    review_relative = str(review_file.resolve().relative_to(root))
    state_file = state_path(runs_dir, run_id, topic_id)
    state = yaml.safe_load(state_file.read_text()) if state_file.exists() else {
        "contract_version": "1", "run_id": run_id, "topic_id": topic_id,
        "status": "running", "completed_stages": [],
    }
    if review is not None:
        _atomic_write(review_file, review)
    state["completed_stages"] = [*state.get("completed_stages", []), stage]
    state["current_stage"] = CANONICAL_STAGES[min(CANONICAL_STAGES.index(stage) + 1, len(CANONICAL_STAGES) - 1)]
    state["checkpoint"] = {
        "stage": stage, "cycle": cycle, "result": result,
        "last_artifact": artifact_path, "input_fingerprint": digest,
        "paths": [artifact_path, result_relative] + ([review_relative] if review is not None else []),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_write(state_file, state)
    event = {
        "event_id": f"evt_{len(existing['events']) + 1:04d}",
        "idempotency_key": key, "stage": stage, "cycle": cycle,
        "artifact_path": artifact_path, "result_path": result_relative,
        "review_path": review_relative if review is not None else None,
    }
    existing["events"].append(event)
    _atomic_write(events, existing)
    manifest["persistence_order"] = PERSISTENCE_ORDER
    for item in manifest["queue"]:
        if item["topic_id"] == topic_id:
            item["status"] = "completed" if stage == "approval_humana" else "running"
            item["current_stage"] = state["current_stage"]
    _atomic_write(manifest_path, manifest)
    return manifest
