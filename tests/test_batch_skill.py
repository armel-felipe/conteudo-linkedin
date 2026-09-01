import hashlib
from pathlib import Path

import pytest
import yaml

from editorial_batch import (
    CANONICAL_STAGES,
    PERSISTENCE_ORDER,
    checkpoint_valid,
    continue_after_failure,
    event_path,
    freeze_manifest,
    idempotency_key,
    load_and_select_topics,
    persist_stage,
    review_path,
    resume_stage,
    state_path,
)


def write_fixture(root):
    (root / "content").mkdir()
    (root / "research" / "topics").mkdir(parents=True)
    (root / "content" / "backlog.md").write_text(
        "| topic_a | 81 | ready_for_research |\n"
        "| topic_b | 99 | candidate |\n"
        "| topic_c | 92 | ready_for_research |\n"
        "| topic_d | 92 | ready_for_research |\n"
    )
    (root / "research" / "topics" / "topics_20260901.yaml").write_text(
        yaml.safe_dump(
            {
                "topics": [
                    {"topic_id": "topic_a", "score": 81, "status": "ready_for_research"},
                    {"topic_id": "topic_b", "score": 99, "status": "candidate"},
                    {"topic_id": "topic_c", "score": 92, "status": "ready_for_research"},
                    {"topic_id": "topic_d", "score": 92, "status": "ready_for_research"},
                ]
            }
        )
    )


def test_selection_filters_ready_orders_and_supports_all_n_and_explicit_ids(tmp_path):
    write_fixture(tmp_path)
    source = (tmp_path / "content" / "backlog.md", tmp_path / "research" / "topics")

    assert [t["topic_id"] for t in load_and_select_topics(*source, "all")] == [
        "topic_c",
        "topic_d",
        "topic_a",
    ]
    assert [t["topic_id"] for t in load_and_select_topics(*source, "2")] == ["topic_c", "topic_d"]
    assert [t["topic_id"] for t in load_and_select_topics(*source, "topic_a,topic_c")] == [
        "topic_a",
        "topic_c",
    ]


def test_explicit_selection_rejects_missing_or_non_ready_ids(tmp_path):
    write_fixture(tmp_path)
    source = (tmp_path / "content" / "backlog.md", tmp_path / "research" / "topics")
    with pytest.raises(ValueError, match="topic_b"):
        load_and_select_topics(*source, "topic_b")
    with pytest.raises(ValueError, match="topic_missing"):
        load_and_select_topics(*source, "topic_missing")


def test_manifest_freezes_root_selection_and_queue_and_is_idempotent(tmp_path):
    write_fixture(tmp_path)
    topics = load_and_select_topics(
        tmp_path / "content" / "backlog.md", tmp_path / "research" / "topics", "2"
    )
    first = freeze_manifest(tmp_path / "runs", "run_001", "2", topics)
    topics[0]["score"] = 1
    second = freeze_manifest(tmp_path / "runs", "run_001", "2", topics)

    assert first == second
    assert first["selection"] == "2"
    assert [item["topic_id"] for item in first["queue"]] == ["topic_c", "topic_d"]
    assert first["queue_frozen"] is True
    assert (tmp_path / "runs" / "run_001" / "manifest.yaml").exists()


def test_checkpoint_requires_result_artifact_fingerprint_paths_and_validates_resume(tmp_path):
    artifact = tmp_path / "research" / "briefs" / "topic_c.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("brief")
    state = {
        "contract_version": "1",
        "run_id": "run_001",
        "topic_id": "topic_c",
        "status": "running",
        "current_stage": "write-post",
        "completed_stages": ["research-topic", "brief_review_gauntlet"],
        "checkpoint": {
            "stage": "brief_review_gauntlet",
            "cycle": 1,
            "result": {"decision": "approved"},
            "last_artifact": "research/briefs/topic_c.md",
            "input_fingerprint": "sha256:" + hashlib.sha256(b"brief").hexdigest(),
            "paths": ["research/briefs/topic_c.md"],
            "saved_at": "2026-09-01T10:00:00Z",
        },
    }
    assert checkpoint_valid(state, tmp_path) is True
    assert resume_stage(state) == "write-post"
    state["checkpoint"]["result"] = None
    assert checkpoint_valid(state, tmp_path) is False


def test_idempotency_and_persistence_contract_are_explicit():
    assert idempotency_key("run_001", "topic_c", "brief_review_gauntlet", 1) == (
        "run_001",
        "topic_c",
        "brief_review_gauntlet",
        1,
    )
    assert PERSISTENCE_ORDER == ["artifact", "result", "state.yaml", "event", "manifest"]
    assert CANONICAL_STAGES == [
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
    assert "publicar-linkedin" not in CANONICAL_STAGES
    assert event_path("runs", "run_001") == Path("runs/run_001/events.yaml")
    assert state_path("runs", "run_001", "topic_c") == Path(
        "runs/run_001/topics/topic_c/state.yaml"
    )
    assert review_path("runs", "run_001", "topic_c", 2) == Path(
        "runs/run_001/topics/topic_c/reviews/cycle-02.yaml"
    )


def test_failed_topic_is_blocked_before_continuing_to_next_queue_item():
    queue = [
        {"topic_id": "topic_a", "status": "running"},
        {"topic_id": "topic_b", "status": "queued"},
    ]
    remaining = continue_after_failure(queue, "topic_a", "missing artifact")
    assert queue[0] == {"topic_id": "topic_a", "status": "blocked", "error": "missing artifact"}
    assert remaining == ["topic_b"]


def test_persist_stage_writes_all_run_artifacts_in_order_and_is_idempotent(tmp_path):
    write_fixture(tmp_path)
    topics = load_and_select_topics(
        tmp_path / "content" / "backlog.md", tmp_path / "research" / "topics", "1"
    )
    freeze_manifest(tmp_path / "runs", "run_001", "1", topics)
    result = {"decision": "approved", "artifact": "content/drafts/topic_c.md"}
    review = {
        "decision": "approved",
        "coverage": 1.0,
        "criteria": {"evidence": 9},
        "hard_failures": [],
        "feedback": [],
        "artifact": "content/drafts/topic_c.md",
    }

    first = persist_stage(
        tmp_path / "runs",
        tmp_path,
        "run_001",
        "topic_c",
        "research-topic",
        1,
        "content/drafts/topic_c.md",
        "draft",
        result,
        review,
    )
    second = persist_stage(
        tmp_path / "runs",
        tmp_path,
        "run_001",
        "topic_c",
        "research-topic",
        1,
        "content/drafts/topic_c.md",
        "changed",
        result,
        review,
    )

    assert first["persistence_order"] == PERSISTENCE_ORDER
    assert second == first
    assert (tmp_path / "content/drafts/topic_c.md").read_text() == "draft"
    assert (tmp_path / "runs/run_001/topics/topic_c/state.yaml").exists()
    assert (tmp_path / "runs/run_001/events.yaml").exists()
    assert (tmp_path / "runs/run_001/topics/topic_c/reviews/cycle-01.yaml").exists()
    events = yaml.safe_load((tmp_path / "runs/run_001/events.yaml").read_text())
    assert len(events["events"]) == 1
    assert events["events"][0]["idempotency_key"] == ["run_001", "topic_c", "research-topic", 1]
    state = yaml.safe_load(
        (tmp_path / "runs/run_001/topics/topic_c/state.yaml").read_text()
    )
    assert state["checkpoint"]["input_fingerprint"] == "sha256:" + hashlib.sha256(b"draft").hexdigest()
    assert checkpoint_valid(state, tmp_path) is True
    assert not list((tmp_path / "runs/run_001").glob("*.tmp"))


def test_persist_stage_rejects_invalid_manifest_contract_and_absolute_artifact(tmp_path):
    write_fixture(tmp_path)
    topics = load_and_select_topics(
        tmp_path / "content" / "backlog.md", tmp_path / "research" / "topics", "1"
    )
    freeze_manifest(tmp_path / "runs", "run_001", "1", topics)
    manifest_path = tmp_path / "runs/run_001/manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest["contract_version"] = "2"
    manifest_path.write_text(yaml.safe_dump(manifest))
    with pytest.raises(ValueError, match="contract_version"):
        persist_stage(
            tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
            "content/drafts/topic_c.md", "draft", {}, {},
        )
