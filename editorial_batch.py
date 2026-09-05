"""Small, reusable contracts for selecting and checkpointing editorial batches."""

import os
import re
import tempfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import yaml

from gauntlet_loop import validate_review


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
VALID_STATE_STATUSES = {"running", "blocked", "completed"}


def _valid_id(value, prefix):
    separator = "[-_]" if prefix in {"run_", "topic_"} else "_"
    stem = prefix.rstrip("_-")
    return isinstance(value, str) and re.fullmatch(rf"{stem}{separator}[A-Za-z0-9_]+", value) is not None


def _queue_fingerprint(queue):
    immutable_queue = [
        {"topic_id": item.get("topic_id"), "position": item.get("position"), "score": item.get("score")}
        for item in queue
    ]
    payload = yaml.safe_dump(immutable_queue, sort_keys=True).encode()
    return "sha256:" + sha256(payload).hexdigest()


def _valid_relative_file(root, relative_path):
    if not _clean_relative_path(relative_path):
        return False
    candidate = (root / relative_path).resolve()
    return root in candidate.parents and candidate.is_file()


def _clean_relative_path(value):
    return (
        isinstance(value, str)
        and value
        and not Path(value).is_absolute()
        and all(part not in {".", ".."} for part in Path(value).parts)
    )


def _review_passes(review, artifact_path):
    if not _review_is_structural(review, artifact_path):
        return False
    return (
        review.get("artifact") == artifact_path
        and review.get("decision") == "approved"
        and review.get("coverage", 0) >= 0.99
        and all(score >= 9 for score in review["criteria"].values())
        and review.get("hard_failures") == []
        and review.get("feedback") == []
    )


def _review_is_structural(review, artifact_path):
    return isinstance(review, dict) and validate_review(review)["valid"] and review.get("artifact") == artifact_path


def _valid_commit_event(event, root=None):
    required = {
        "event_id", "phase", "idempotency_key", "stage", "cycle", "artifact_path",
        "result_path", "review_path", "committed_at", "result", "review",
    }
    if (not isinstance(event, dict) or set(event) != required or event.get("phase") != "commit"
            or not isinstance(event.get("event_id"), str)
            or re.fullmatch(r"evt_[0-9]{4}", event["event_id"]) is None):
        return False
    try:
        committed_at = datetime.fromisoformat(event["committed_at"])
    except (TypeError, ValueError):
        return False
    if committed_at.tzinfo is None or committed_at.utcoffset() is None:
        return False
    key = event["idempotency_key"]
    if (not isinstance(key, list) or len(key) != 4 or not _valid_id(key[0], "run_")
            or not _valid_id(key[1], "topic_") or key[2] not in CANONICAL_STAGES
            or isinstance(key[3], bool) or not isinstance(key[3], int) or key[3] < 1):
        return False
    if event["stage"] != key[2] or event["cycle"] != key[3]:
        return False
    if (not _clean_relative_path(event.get("artifact_path"))
            or event["result_path"] != _canonical_result_path(*key)):
        return False
    expected_review_path = str(Path("runs") / key[0] / "topics" / key[1] / "reviews" / f"cycle-{key[3]:02d}.yaml")
    if event["review_path"] != expected_review_path:
        return False
    if (not isinstance(event["result"], dict)
            or event["result"].get("artifact") != event["artifact_path"]
            or not _review_passes(event["review"], event["artifact_path"])):
        return False
    if root is not None:
        try:
            return (_valid_relative_file(root, event["artifact_path"])
                    and _valid_relative_file(root, event["result_path"])
                    and _load_yaml(root / event["result_path"], "result") == event["result"]
                    and _valid_relative_file(root, event["review_path"])
                    and _load_yaml(root / event["review_path"], "review") == event["review"])
        except ValueError:
            return False
    return True


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
        if count == 0:
            raise ValueError("numeric selection must be positive")
        ordered = sorted(eligible, key=lambda topic_id: (-eligible[topic_id]["score"], topic_id))
        chosen_ids = ordered[:count]
    else:
        chosen_ids = [topic_id.strip() for topic_id in selection.split(",") if topic_id.strip()]
        if len(chosen_ids) != len(set(chosen_ids)):
            raise ValueError("explicit selection contains duplicate topic ids")
        invalid = [
            topic_id
            for topic_id in chosen_ids
            if topic_id not in eligible
        ]
        if invalid:
            raise ValueError(f"invalid or non-ready topic ids: {', '.join(invalid)}")

    if not chosen_ids:
        raise ValueError("selection must not be empty")

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
    manifest["queue_fingerprint"] = _queue_fingerprint(manifest["queue"])
    _atomic_write(path, manifest)
    return manifest


def checkpoint_valid(state, workspace_root):
    checkpoint = state.get("checkpoint", {})
    if (state.get("contract_version") != "1" or not _valid_id(state.get("run_id"), "run_")
            or not _valid_id(state.get("topic_id"), "topic_")):
        return False
    result = checkpoint.get("result")
    if not isinstance(result, dict) or not result or not checkpoint.get("last_artifact"):
        return False
    if (
        isinstance(checkpoint.get("cycle"), bool)
        or not isinstance(checkpoint.get("cycle"), int)
        or checkpoint["cycle"] < 1
    ):
        return False
    fingerprint = checkpoint.get("input_fingerprint", "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", fingerprint):
        return False
    stage = checkpoint.get("stage")
    if (not checkpoint.get("saved_at") or stage not in CANONICAL_STAGES
            or stage not in state.get("completed_stages", [])
            or state.get("status") not in VALID_STATE_STATUSES
            or not isinstance(state.get("completed_stages"), list)
            or any(item not in CANONICAL_STAGES for item in state["completed_stages"])):
        return False
    expected_current = None if stage == CANONICAL_STAGES[-1] else CANONICAL_STAGES[CANONICAL_STAGES.index(stage) + 1]
    if state.get("status") == "completed" and expected_current is not None:
        return False
    if state.get("status") == "running" and state.get("current_stage") != expected_current:
        return False
    if state.get("status") == "blocked" and state.get("current_stage") != stage:
        return False
    if result.get("artifact") != checkpoint.get("last_artifact"):
        return False
    root = Path(workspace_root).resolve()
    expected_review_path = str(Path("runs") / state["run_id"] / "topics" / state["topic_id"] / "reviews" / f"cycle-{checkpoint['cycle']:02d}.yaml")
    if checkpoint.get("result_path") != _canonical_result_path(
        state["run_id"], state["topic_id"], stage, checkpoint["cycle"]
    ) or checkpoint.get("review_path") != expected_review_path:
        return False
    paths = checkpoint.get("paths")
    if paths != [checkpoint["last_artifact"], checkpoint["result_path"], checkpoint["review_path"]]:
        return False
    paths = [checkpoint["last_artifact"], *paths[1:]]
    for relative_path in paths:
        if not _clean_relative_path(relative_path):
            return False
        candidate = (root / relative_path).resolve()
        if root not in candidate.parents or not candidate.is_file():
            return False
    result_path = checkpoint.get("result_path")
    expected_result_path = _canonical_result_path(
        state["run_id"], state["topic_id"], checkpoint["stage"], checkpoint["cycle"]
    )
    if result_path != expected_result_path or Path(result_path).is_absolute():
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
    review_path_value = (root / checkpoint["review_path"]).resolve()
    try:
        review = _load_yaml(review_path_value, "review")
        if review != checkpoint.get("review") or not _review_passes(review, checkpoint["last_artifact"]):
            return False
    except ValueError:
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
    if (manifest.get("run_id") != run_id or not _valid_id(run_id, "run_")
            or not manifest.get("queue_frozen") or not isinstance(manifest.get("queue"), list)
            or manifest.get("queue_fingerprint") != _queue_fingerprint(manifest["queue"])):
        raise ValueError("manifest ids or frozen queue are invalid")
    for position, item in enumerate(manifest["queue"], start=1):
        if (not isinstance(item, dict) or not _valid_id(item.get("topic_id"), "topic_")
                or item.get("position") != position or item.get("status") not in {"queued", "running", "blocked", "completed"}
                or item.get("current_stage") not in CANONICAL_STAGES + [None]):
            raise ValueError("manifest frozen queue is invalid")
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


def _canonical_result_path(run_id, topic_id, stage, cycle):
    return str(Path("runs") / run_id / "topics" / topic_id / "results" / f"{stage}-cycle-{cycle:02d}.yaml")


def _valid_review(review, artifact_path):
    return _review_passes(review, artifact_path)


def _update_metrics(manifest, events, root):
    metrics = manifest.setdefault("metrics", {**DEFAULT_METRICS, "queue_size": len(manifest["queue"])})
    valid_events = [event for event in events if _valid_commit_event(event, root)]
    reviews = [event["review"] for event in valid_events]
    coverages = [review["coverage"] for review in reviews if isinstance(review.get("coverage"), (int, float))]
    metrics["reviewer_coverage"] = sum(coverages) / len(coverages) if coverages else 0.0
    human = [
        event["review"]["coverage"] for event in valid_events
        if str(event.get("stage", "")).startswith("humanize_review_")
        and isinstance(event["review"].get("coverage"), (int, float))
    ]
    metrics["human_writing_conformity"] = sum(human) / len(human) if human else 0.0
    committed_cycles = {
        event.get("stage"): event.get("cycle")
        for event in valid_events
    }
    metrics["cycles_per_stage"] = {
        stage: max(
            event["cycle"]
            for event in valid_events
            if event.get("stage") == stage
        )
        for stage in committed_cycles
    }
    approval = next((event for event in valid_events if event.get("stage") == "approval_humana"), None)
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
    if state.get("status") == "completed":
        raise ValueError("terminal state cannot transition")
    if (state.get("contract_version") != "1" or state.get("run_id") != run_id
            or state.get("topic_id") != topic_id):
        raise ValueError("state ids are invalid")
    if state.get("status") == "blocked" and state.get("current_stage") not in CANONICAL_STAGES:
        raise ValueError("blocked current_stage is invalid")
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
    if state["status"] == "blocked" and state.get("current_stage") not in CANONICAL_STAGES:
        raise ValueError("blocked current_stage is invalid")
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
            "stage": state.get("current_stage") or checkpoint.get("stage") or item.get("current_stage"),
            "current_stage": state.get("current_stage") or checkpoint.get("stage") or item.get("current_stage"),
        })
        _atomic_write(events_path, events)
    item.update(status="blocked", current_stage=state.get("current_stage"), error=error)
    metrics = manifest.setdefault("metrics", {**DEFAULT_METRICS, "queue_size": len(manifest["queue"])})
    metrics["queue_size"] = len(manifest["queue"])
    metrics["completed"] = sum(entry["status"] == "completed" for entry in manifest["queue"])
    metrics["blocked"] = sum(entry["status"] == "blocked" for entry in manifest["queue"])
    _update_metrics(manifest, events["events"], workspace_root)
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
    if not _valid_id(run_id, "run_") or not _valid_id(topic_id, "topic_"):
        raise ValueError("run or topic id is invalid")
    if stage not in CANONICAL_STAGES:
        raise ValueError(f"unknown stage: {stage}")
    if not _clean_relative_path(artifact_path):
        raise ValueError("artifact path must be clean relative path")
    if not _review_is_structural(review, artifact_path):
        raise ValueError("review is invalid")
    if not _review_passes(review, artifact_path):
        raise ValueError("review quality gate failed")
    if not isinstance(result, dict) or result.get("artifact") != artifact_path:
        raise ValueError("result artifact is invalid")
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
    if (state.get("contract_version") != "1" or state.get("run_id") != run_id
            or state.get("topic_id") != topic_id):
        raise ValueError("state ids are invalid")
    if state.get("status") not in {None, *VALID_STATE_STATUSES}:
        raise ValueError("state status is invalid")
    if state.get("status") in {"blocked", "completed"}:
        raise ValueError("terminal state cannot transition")
    events = event_path(runs_dir, run_id)
    existing = _load_events(events)
    if any(event.get("phase") == "commit" and not _valid_commit_event(event) for event in existing["events"]):
        raise ValueError("event commit is invalid")
    key = list(idempotency_key(run_id, topic_id, stage, cycle))
    result_file = Path(runs_dir) / run_id / "topics" / topic_id / "results" / f"{stage}-cycle-{cycle:02d}.yaml"
    result_relative = _canonical_result_path(run_id, topic_id, stage, cycle)
    review_file = review_path(runs_dir, run_id, topic_id, cycle)
    review_relative = str(review_file.resolve().relative_to(root))
    pending_intent = next(
        (event for event in existing["events"] if event.get("idempotency_key") == key and event.get("phase") == "intent"),
        None,
    )
    expected_intent = {
        "idempotency_key": key, "stage": stage, "cycle": cycle,
        "artifact_path": artifact_path, "result_path": result_relative,
        "review_path": review_relative, "result": result, "review": review,
    }
    if pending_intent and any(pending_intent.get(name) != value for name, value in expected_intent.items()):
        raise ValueError("intent path or payload is divergent")
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
            if (stored_result != result or stored_review != review or event.get("result") != result
                    or event.get("review") != review):
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
    pending_paths = [artifact, result_file, review_file]
    if pending_intent and any(path.exists() for path in pending_paths):
        if (not all(path.is_file() for path in pending_paths)
                or artifact.read_bytes() != str(artifact_content).encode()
                or _load_yaml(result_file, "result") != result
                or _load_yaml(review_file, "review") != review):
            raise ValueError("partial recovery payload is divergent")

    intent = pending_intent or {
        "event_id": f"evt_{len(existing['events']) + 1:04d}",
        "phase": "intent", "idempotency_key": key, "stage": stage, "cycle": cycle,
        "artifact_path": artifact_path, "result_path": result_relative,
        "review_path": review_relative, "result": result, "review": review,
    }
    if pending_intent is None:
        existing["events"].append(intent)
        _atomic_write(events, existing)

    state["status"] = "running"
    _atomic_write_bytes(artifact, str(artifact_content).encode())
    _atomic_write(result_file, result)
    digest = "sha256:" + sha256(artifact.read_bytes()).hexdigest()
    _atomic_write(review_file, review)
    state["completed_stages"] = [*state.get("completed_stages", []), stage]
    state["current_stage"] = None if stage == "approval_humana" else CANONICAL_STAGES[CANONICAL_STAGES.index(stage) + 1]
    state["checkpoint"] = {
        "stage": stage, "cycle": cycle, "result": result,
        "review": review,
        "last_artifact": artifact_path, "input_fingerprint": digest,
        "result_path": result_relative, "review_path": review_relative,
        "paths": [artifact_path, result_relative] + ([review_relative] if review is not None else []),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_write(state_file, state)
    commit = dict(intent)
    commit["event_id"] = f"evt_{len(existing['events']) + 1:04d}"
    commit["phase"] = "commit"
    commit.update({"artifact_path": artifact_path, "result_path": result_relative, "review_path": review_relative})
    commit["committed_at"] = datetime.now(timezone.utc).isoformat()
    commit["result"] = result
    commit["review"] = review
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
    _update_metrics(manifest, existing["events"], root)
    _atomic_write(events, existing)
    _atomic_write(manifest_path, manifest)
    return manifest
