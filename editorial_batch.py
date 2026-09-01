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
DEFAULT_METRICS = {
    "queue_size": 0,
    "completed": 0,
    "blocked": 0,
    "cycles_per_stage": {},
    "reviewer_coverage": 0.0,
    "human_writing_conformity": 0.0,
    "time_to_approval": None,
}


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
        return _load_manifest(path, run_id)

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
        "metrics": {**DEFAULT_METRICS, "queue_size": len(topics)},
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
    if checkpoint.get("result", {}).get("artifact") != checkpoint.get("last_artifact"):
        return False
    root = Path(workspace_root).resolve()
    paths = [checkpoint["last_artifact"], *checkpoint.get("paths", [])]
    for relative_path in paths:
        if Path(relative_path).is_absolute():
            return False
        candidate = (root / relative_path).resolve()
        if root not in candidate.parents or not candidate.is_file():
            return False
    result_path = checkpoint.get("result_path")
    if result_path:
        if Path(result_path).is_absolute():
            return False
        result_file = (root / result_path).resolve()
        if root not in result_file.parents or not result_file.is_file():
            return False
        try:
            if _load_yaml(result_file, "result") != checkpoint["result"]:
                return False
        except ValueError:
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


def _load_manifest(manifest_path, run_id):
    try:
        manifest = yaml.safe_load(manifest_path.read_text())
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise ValueError("manifest is corrupt or missing") from exc
    if not isinstance(manifest, dict) or manifest.get("contract_version") != "1":
        raise ValueError("manifest contract_version must be 1")
    if manifest.get("run_id") != run_id or not manifest.get("queue_frozen"):
        raise ValueError("manifest ids or frozen queue are invalid")
    return manifest


def _load_events(events_path):
    if not events_path.exists():
        return {"contract_version": "1", "events": []}
    try:
        events = yaml.safe_load(events_path.read_text())
    except yaml.YAMLError as exc:
        raise ValueError("events are corrupt") from exc
    if not isinstance(events, dict) or events.get("contract_version") != "1" or not isinstance(events.get("events"), list):
        raise ValueError("events are invalid")
    return events


def _load_yaml(path, label):
    try:
        value = yaml.safe_load(path.read_text())
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise ValueError(f"{label} is corrupt or missing") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} is invalid")
    return value


def _valid_review(review, artifact_path):
    required = {"decision", "coverage", "criteria", "hard_failures", "feedback", "artifact"}
    return (
        isinstance(review, dict)
        and required <= set(review)
        and review["decision"] in {"approved", "feedback"}
        and isinstance(review["feedback"], list)
        and review["artifact"] == artifact_path
    )


def _update_metrics(manifest, events):
    metrics = manifest.setdefault("metrics", {**DEFAULT_METRICS, "queue_size": len(manifest["queue"])})
    reviews = [event["review"] for event in events if event.get("phase") == "commit" and isinstance(event.get("review"), dict)]
    coverages = [review["coverage"] for review in reviews if isinstance(review.get("coverage"), (int, float))]
    metrics["reviewer_coverage"] = sum(coverages) / len(coverages) if coverages else 0.0
    human = [
        event["review"]["coverage"] for event in events
        if event.get("phase") == "commit"
        and str(event.get("stage", "")).startswith("humanize_review_")
        and isinstance(event.get("review"), dict)
        and isinstance(event["review"].get("coverage"), (int, float))
    ]
    metrics["human_writing_conformity"] = sum(human) / len(human) if human else 0.0
    approval = next((event for event in events if event.get("phase") == "commit" and event.get("stage") == "approval_humana"), None)
    if approval:
        try:
            started = datetime.fromisoformat(manifest["created_at"])
            finished = datetime.fromisoformat(approval["committed_at"])
            seconds = max(0, int((finished - started).total_seconds()))
            metrics["time_to_approval"] = f"PT{seconds}S"
        except (KeyError, TypeError, ValueError):
            metrics["time_to_approval"] = None


def continue_after_failure(
    runs_dir, workspace_root, run_id, topic_id, error, *,
    artifact_fingerprint=None, review=None, feedback=None, cycle_count=0,
):
    manifest_path = Path(runs_dir) / run_id / "manifest.yaml"
    manifest = _load_manifest(manifest_path, run_id)
    item = next((item for item in manifest["queue"] if item["topic_id"] == topic_id), None)
    if item is None:
        raise ValueError("topic is not in manifest")
    state_file = state_path(runs_dir, run_id, topic_id)
    state = _load_yaml(state_file, "state") if state_file.exists() else {
        "contract_version": "1", "run_id": run_id, "topic_id": topic_id,
        "completed_stages": [],
    }
    if state.get("contract_version") != "1" or state.get("run_id") != run_id or state.get("topic_id") != topic_id:
        raise ValueError("state ids are invalid")
    checkpoint = state.get("checkpoint", {})
    state.update(
        status="blocked",
        current_stage=state.get("current_stage") or checkpoint.get("stage") or item.get("current_stage"),
        failure={"error": error},
        artifact_fingerprint=artifact_fingerprint or checkpoint.get("input_fingerprint"),
        last_review=review if review is not None else state.get("last_review"),
        feedback=feedback if feedback is not None else state.get("feedback", []),
        cycle_count=cycle_count or state.get("cycle_count") or checkpoint.get("cycle", 0),
    )
    _atomic_write(state_file, state)
    events_path = event_path(runs_dir, run_id)
    events = _load_events(events_path)
    key = list(idempotency_key(run_id, topic_id, "blocked", 0))
    if not any(event.get("idempotency_key") == key and event.get("phase") == "commit" for event in events["events"]):
        events["events"].append({
            "event_id": f"evt_{len(events['events']) + 1:04d}",
            "type": "topic_blocked", "phase": "commit", "idempotency_key": key,
            "error": error, "artifact_fingerprint": state.get("artifact_fingerprint"),
            "last_review": state.get("last_review"), "feedback": state.get("feedback", []),
            "cycle_count": state.get("cycle_count", 0),
        })
        _atomic_write(events_path, events)
    item.update(status="blocked", current_stage=None, error=error)
    metrics = manifest.setdefault("metrics", {**DEFAULT_METRICS, "queue_size": len(manifest["queue"])})
    metrics["queue_size"] = len(manifest["queue"])
    metrics["completed"] = sum(entry["status"] == "completed" for entry in manifest["queue"])
    metrics["blocked"] = sum(entry["status"] == "blocked" for entry in manifest["queue"])
    _atomic_write(manifest_path, manifest)
    return [entry["topic_id"] for entry in manifest["queue"] if entry["status"] == "queued"]


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
    manifest = _load_manifest(manifest_path, run_id)
    queue_item = next((item for item in manifest["queue"] if item["topic_id"] == topic_id), None)
    if queue_item is None:
        raise ValueError("manifest ids do not match stage")
    state_file = state_path(runs_dir, run_id, topic_id)
    state = _load_yaml(state_file, "state") if state_file.exists() else {
        "contract_version": "1", "run_id": run_id, "topic_id": topic_id,
        "status": "running", "current_stage": queue_item.get("current_stage", "research-topic"),
        "completed_stages": [],
    }
    if state.get("contract_version") != "1" or state.get("run_id") != run_id or state.get("topic_id") != topic_id:
        raise ValueError("state ids are invalid")
    events = event_path(runs_dir, run_id)
    existing = _load_events(events)
    key = list(idempotency_key(run_id, topic_id, stage, cycle))
    result_file = Path(runs_dir) / run_id / "topics" / topic_id / "results" / f"{stage}-cycle-{cycle:02d}.yaml"
    result_relative = str(result_file.resolve().relative_to(root))
    review_file = review_path(runs_dir, run_id, topic_id, cycle)
    review_relative = str(review_file.resolve().relative_to(root))
    pending_intent = next(
        (event for event in existing["events"] if event.get("idempotency_key") == key and event.get("phase") == "intent"),
        None,
    )
    for event in existing["events"]:
        if event.get("idempotency_key") == key and event.get("phase") == "commit":
            expected_paths = {
                "artifact_path": artifact_path,
                "result_path": result_relative,
                "review_path": review_relative,
            }
            if any(event.get(name) != value for name, value in expected_paths.items()):
                raise ValueError("checkpoint is divergent")
            stored_result = _load_yaml(root / event["result_path"], "result")
            stored_review = _load_yaml(root / event["review_path"], "review")
            if stored_result != result or stored_review != review:
                raise ValueError("checkpoint payload is divergent")
            state = _load_yaml(state_file, "state")
            if not checkpoint_valid(state, root) or state["checkpoint"].get("stage") != stage:
                raise ValueError("checkpoint fingerprint is divergent")
            return manifest
    expected_stage = state.get("current_stage", queue_item.get("current_stage"))
    if stage != expected_stage:
        raise ValueError("stage does not match current_stage")
    if any(prerequisite not in state.get("completed_stages", []) for prerequisite in CANONICAL_STAGES[:CANONICAL_STAGES.index(stage)]):
        raise ValueError("stage prerequisites are incomplete")
    if not _valid_review(review, artifact_path):
        raise ValueError("review is invalid")

    state["status"] = "running"
    _atomic_write_bytes(artifact, str(artifact_content).encode())
    _atomic_write(result_file, result)
    digest = "sha256:" + sha256(artifact.read_bytes()).hexdigest()
    _atomic_write(review_file, review)
    state["completed_stages"] = [*state.get("completed_stages", []), stage]
    state["current_stage"] = None if stage == "approval_humana" else CANONICAL_STAGES[CANONICAL_STAGES.index(stage) + 1]
    state["checkpoint"] = {
        "stage": stage, "cycle": cycle, "result": result,
        "last_artifact": artifact_path, "input_fingerprint": digest,
        "result_path": result_relative, "review_path": review_relative,
        "paths": [artifact_path, result_relative] + ([review_relative] if review is not None else []),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_write(state_file, state)
    intent = pending_intent or {
        "event_id": f"evt_{len(existing['events']) + 1:04d}",
        "phase": "intent", "idempotency_key": key, "stage": stage, "cycle": cycle,
        "artifact_path": artifact_path, "result_path": result_relative,
        "review_path": review_relative,
    }
    if pending_intent is None:
        existing["events"].append(intent)
        _atomic_write(events, existing)
    commit = dict(intent)
    commit["event_id"] = f"evt_{len(existing['events']) + 1:04d}"
    commit["phase"] = "commit"
    commit.update({"artifact_path": artifact_path, "result_path": result_relative, "review_path": review_relative})
    commit["committed_at"] = datetime.now(timezone.utc).isoformat()
    existing["events"].append(commit)
    _atomic_write(events, existing)
    manifest["persistence_order"] = PERSISTENCE_ORDER
    for item in manifest["queue"]:
        if item["topic_id"] == topic_id:
            item["status"] = "completed" if stage == "approval_humana" else "running"
            item["current_stage"] = state["current_stage"]
    metrics = manifest.setdefault("metrics", {**DEFAULT_METRICS, "queue_size": len(manifest["queue"])})
    metrics["queue_size"] = len(manifest["queue"])
    metrics["completed"] = sum(item["status"] == "completed" for item in manifest["queue"])
    metrics["blocked"] = sum(item["status"] == "blocked" for item in manifest["queue"])
    metrics["cycles_per_stage"][stage] = max(metrics["cycles_per_stage"].get(stage, 0), cycle)
    existing["events"][-1]["stage"] = stage
    existing["events"][-1]["review"] = review
    _update_metrics(manifest, existing["events"])
    _atomic_write(events, existing)
    _atomic_write(manifest_path, manifest)
    return manifest
