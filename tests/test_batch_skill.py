import hashlib
from pathlib import Path

import pytest
import yaml

from editorial_batch import (
    CANONICAL_STAGES,
    DEFAULT_METRICS,
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
    _update_metrics,
    _valid_commit_event,
)
from gauntlet_loop import NORMATIVE_CRITERIA


def valid_review(artifact):
    return {
        "decision": "approved",
        "coverage": 1.0,
        "criteria": {criterion: 10 for criterion in NORMATIVE_CRITERIA},
        "hard_failures": [],
        "feedback": [],
        "artifact": artifact,
    }


def valid_result(artifact):
    return {"artifact": artifact}


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
            "result": {"decision": "approved", "artifact": "research/briefs/topic_c.md"},
            "last_artifact": "research/briefs/topic_c.md",
            "input_fingerprint": "sha256:" + hashlib.sha256(b"brief").hexdigest(),
            "result_path": "runs/run_001/topics/topic_c/results/brief_review_gauntlet-cycle-01.yaml",
            "review_path": "runs/run_001/topics/topic_c/reviews/cycle-01.yaml",
            "review": valid_review("research/briefs/topic_c.md"),
            "paths": ["research/briefs/topic_c.md", "runs/run_001/topics/topic_c/results/brief_review_gauntlet-cycle-01.yaml", "runs/run_001/topics/topic_c/reviews/cycle-01.yaml"],
            "saved_at": "2026-09-01T10:00:00Z",
        },
    }
    result_file = tmp_path / "runs/run_001/topics/topic_c/results/brief_review_gauntlet-cycle-01.yaml"
    result_file.parent.mkdir(parents=True)
    result_file.write_text(yaml.safe_dump(state["checkpoint"]["result"]))
    review_file = tmp_path / "runs/run_001/topics/topic_c/reviews/cycle-01.yaml"
    review_file.parent.mkdir(parents=True)
    review_file.write_text(yaml.safe_dump(state["checkpoint"]["review"]))
    assert checkpoint_valid(state, tmp_path) is True
    assert resume_stage(state) == "write-post"
    state["checkpoint"]["stage"] = "write-post"
    assert checkpoint_valid(state, tmp_path) is False


def test_checkpoint_without_result_path_is_invalid(tmp_path):
    artifact = tmp_path / "brief.md"
    artifact.write_text("brief")
    state = {
        "contract_version": "1", "run_id": "run", "topic_id": "topic",
        "completed_stages": ["research-topic"],
        "checkpoint": {
            "stage": "research-topic", "cycle": 1,
            "result": {"ok": True}, "last_artifact": "brief.md",
            "input_fingerprint": "sha256:" + hashlib.sha256(b"brief").hexdigest(),
            "paths": ["brief.md"], "saved_at": "now",
        },
    }
    assert checkpoint_valid(state, tmp_path) is False
    state["checkpoint"]["stage"] = "brief_review_gauntlet"
    state["checkpoint"]["result"] = None
    assert checkpoint_valid(state, tmp_path) is False


def test_checkpoint_rejects_result_file_that_diverges_from_canonical_checkpoint(tmp_path):
    artifact = tmp_path / "brief.md"
    artifact.write_text("brief")
    result_path = tmp_path / "result.yaml"
    result = {"decision": "approved", "artifact": "brief.md", "version": 1}
    result_path.write_text(yaml.safe_dump(result))
    state = {
        "contract_version": "1", "run_id": "run", "topic_id": "topic",
        "completed_stages": ["research-topic"],
        "checkpoint": {
            "stage": "research-topic", "cycle": 1, "result": result,
            "last_artifact": "brief.md", "result_path": "result.yaml",
            "input_fingerprint": "sha256:" + hashlib.sha256(b"brief").hexdigest(),
            "paths": ["brief.md", "result.yaml"], "saved_at": "now",
        },
    }
    result_path.write_text(yaml.safe_dump({**result, "version": 2}))
    assert checkpoint_valid(state, tmp_path) is False


def test_blocked_topic_preserves_context_and_can_resume_same_stage(tmp_path):
    write_fixture(tmp_path)
    topics = load_and_select_topics(tmp_path / "content/backlog.md", tmp_path / "research/topics", "1")
    freeze_manifest(tmp_path / "runs", "run_001", "1", topics)
    state_file = tmp_path / "runs/run_001/topics/topic_c/state.yaml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text(yaml.safe_dump({
        "contract_version": "1", "run_id": "run_001", "topic_id": "topic_c",
        "status": "running", "current_stage": "write-post", "completed_stages": [],
    }))
    continue_after_failure(
        tmp_path / "runs", tmp_path, "run_001", "topic_c", "review failed",
        artifact_fingerprint="sha256:" + "a" * 64,
        review={"artifact": "content/draft.md"},
        feedback=[{"criterion": "clareza", "message": "clarify"}],
        cycle_count=2,
    )
    state = yaml.safe_load(state_file.read_text())
    assert state["status"] == "blocked"
    assert state["current_stage"] == "write-post"
    assert state["artifact_fingerprint"] == "sha256:" + "a" * 64
    assert state["last_review"]["artifact"] == "content/draft.md"
    assert state["feedback"][0]["criterion"] == "clareza"
    assert state["cycle_count"] == 2
    manifest = yaml.safe_load((tmp_path / "runs/run_001/manifest.yaml").read_text())
    assert manifest["queue"][0]["current_stage"] == "write-post"
    event = yaml.safe_load((tmp_path / "runs/run_001/events.yaml").read_text())["events"][0]
    assert event["stage"] == "write-post"
    assert event["current_stage"] == "write-post"


def test_blocked_event_is_idempotent_when_failure_is_recorded_again(tmp_path):
    write_fixture(tmp_path)
    topic = load_and_select_topics(tmp_path / "content/backlog.md", tmp_path / "research/topics", "1")
    freeze_manifest(tmp_path / "runs", "run_001", "1", topic)
    continue_after_failure(tmp_path / "runs", tmp_path, "run_001", "topic_c", "failed")
    continue_after_failure(tmp_path / "runs", tmp_path, "run_001", "topic_c", "failed")
    events = yaml.safe_load((tmp_path / "runs/run_001/events.yaml").read_text())["events"]
    assert len([event for event in events if event["type"] == "topic_blocked"]) == 1


def test_commit_event_requires_exact_artifact_result_and_review_paths(tmp_path):
    write_fixture(tmp_path)
    topic = load_and_select_topics(tmp_path / "content/backlog.md", tmp_path / "research/topics", "1")
    freeze_manifest(tmp_path / "runs", "run_001", "1", topic)
    persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                  "content/draft.md", "draft", {"artifact": "content/draft.md"},
                  valid_review("content/draft.md"))
    events_file = tmp_path / "runs/run_001/events.yaml"
    events = yaml.safe_load(events_file.read_text())
    commit = events["events"][-1]
    commit["result_path"] = "content/draft.md"
    events_file.write_text(yaml.safe_dump(events))
    with pytest.raises(ValueError, match="divergent|event"):
        persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                      "content/draft.md", "draft", {"artifact": "content/draft.md"},
                       valid_review("content/draft.md"))


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


def test_failed_topic_is_blocked_before_continuing_to_next_queue_item(tmp_path):
    write_fixture(tmp_path)
    topics = load_and_select_topics(
        tmp_path / "content" / "backlog.md", tmp_path / "research" / "topics", "all"
    )
    freeze_manifest(tmp_path / "runs", "run_001", "all", topics)
    remaining = continue_after_failure(
        tmp_path / "runs", tmp_path, "run_001", "topic_c", "missing artifact"
    )
    state = yaml.safe_load(
        (tmp_path / "runs/run_001/topics/topic_c/state.yaml").read_text()
    )
    manifest = yaml.safe_load((tmp_path / "runs/run_001/manifest.yaml").read_text())
    events = yaml.safe_load((tmp_path / "runs/run_001/events.yaml").read_text())
    assert state["status"] == "blocked"
    assert manifest["queue"][0]["status"] == "blocked"
    assert events["events"][0]["type"] == "topic_blocked"
    assert remaining == ["topic_d", "topic_a"]


def test_persist_stage_writes_all_run_artifacts_in_order_and_is_idempotent(tmp_path):
    write_fixture(tmp_path)
    topics = load_and_select_topics(
        tmp_path / "content" / "backlog.md", tmp_path / "research" / "topics", "1"
    )
    freeze_manifest(tmp_path / "runs", "run_001", "1", topics)
    result = {"decision": "approved", "artifact": "content/drafts/topic_c.md"}
    review = valid_review("content/drafts/topic_c.md")

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
    assert len(events["events"]) == 2
    assert events["events"][-1]["phase"] == "commit"
    assert events["events"][-1]["idempotency_key"] == ["run_001", "topic_c", "research-topic", 1]
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
                "content/drafts/topic_c.md", "draft", valid_result("content/drafts/topic_c.md"), valid_review("content/drafts/topic_c.md"),
        )


def test_persist_stage_enforces_current_stage_and_completed_prerequisites(tmp_path):
    write_fixture(tmp_path)
    topics = load_and_select_topics(
        tmp_path / "content" / "backlog.md", tmp_path / "research" / "topics", "1"
    )
    freeze_manifest(tmp_path / "runs", "run_001", "1", topics)
    with pytest.raises(ValueError, match="current_stage"):
        persist_stage(
            tmp_path / "runs", tmp_path, "run_001", "topic_c", "write-post", 1,
            "content/drafts/topic_c.md", "draft", valid_result("content/drafts/topic_c.md"), valid_review("content/drafts/topic_c.md"),
        )
    state_file = tmp_path / "runs/run_001/topics/topic_c/state.yaml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text(yaml.safe_dump({
        "contract_version": "1", "run_id": "run_001", "topic_id": "topic_c",
        "current_stage": "write-post", "completed_stages": [],
    }))
    with pytest.raises(ValueError, match="prerequisites"):
        persist_stage(
            tmp_path / "runs", tmp_path, "run_001", "topic_c", "write-post", 1,
            "content/drafts/topic_c.md", "draft", valid_result("content/drafts/topic_c.md"), valid_review("content/drafts/topic_c.md"),
        )


def test_persist_stage_rejects_divergent_state_and_recovers_incomplete_event(tmp_path):
    write_fixture(tmp_path)
    topics = load_and_select_topics(
        tmp_path / "content" / "backlog.md", tmp_path / "research" / "topics", "1"
    )
    freeze_manifest(tmp_path / "runs", "run_001", "1", topics)
    state_path_value = tmp_path / "runs/run_001/topics/topic_c/state.yaml"
    state_path_value.parent.mkdir(parents=True)
    state_path_value.write_text(yaml.safe_dump({"contract_version": "1", "run_id": "run_001", "topic_id": "other"}))
    with pytest.raises(ValueError, match="state ids"):
        persist_stage(
            tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
            "content/drafts/topic_c.md", "draft", valid_result("content/drafts/topic_c.md"), valid_review("content/drafts/topic_c.md"),
        )


def test_persist_stage_recovers_intent_event_and_rejects_corrupt_event(tmp_path):
    write_fixture(tmp_path)
    topics = load_and_select_topics(
        tmp_path / "content" / "backlog.md", tmp_path / "research" / "topics", "1"
    )
    freeze_manifest(tmp_path / "runs", "run_001", "1", topics)
    events_path = tmp_path / "runs/run_001/events.yaml"
    events_path.write_text(yaml.safe_dump({"contract_version": "1", "events": [{
        "event_id": "evt_0001",
        "phase": "intent",
        "idempotency_key": ["run_001", "topic_c", "research-topic", 1],
        "stage": "research-topic", "cycle": 1,
        "artifact_path": "content/drafts/topic_c.md",
        "result_path": "runs/run_001/topics/topic_c/results/research-topic-cycle-01.yaml",
        "review_path": "runs/run_001/topics/topic_c/reviews/cycle-01.yaml",
        "result": {"artifact": "content/drafts/topic_c.md"},
        "review": valid_review("content/drafts/topic_c.md"),
    }]}))
    result = {"artifact": "content/drafts/topic_c.md"}
    review = valid_review("content/drafts/topic_c.md")
    persist_stage(
        tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
        "content/drafts/topic_c.md", "draft", result, review,
    )
    events = yaml.safe_load(events_path.read_text())
    assert len(events["events"]) == 2
    assert events["events"][-1]["phase"] == "commit"
    events_path.write_text("not: [valid")
    with pytest.raises(ValueError, match="events"):
        persist_stage(
            tmp_path / "runs", tmp_path, "run_001", "topic_c", "brief_review_gauntlet", 1,
            "content/brief.md", "brief", valid_result("content/brief.md"), valid_review("content/brief.md"),
        )


def test_cycles_per_stage_are_rebuilt_from_committed_events(tmp_path):
    write_fixture(tmp_path)
    topic = load_and_select_topics(tmp_path / "content/backlog.md", tmp_path / "research/topics", "1")
    freeze_manifest(tmp_path / "runs", "run_001", "1", topic)
    persist_stage(
        tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
        "content/research.md", "research", {"artifact": "content/research.md"}, valid_review("content/research.md"),
    )
    events_file = tmp_path / "runs/run_001/events.yaml"
    events = yaml.safe_load(events_file.read_text())
    events["events"].append({"phase": "intent", "stage": "research-topic", "cycle": 99})
    events["events"].append({"phase": "commit", "stage": "research-topic", "cycle": 3})
    events_file.write_text(yaml.safe_dump(events))
    with pytest.raises(ValueError, match="event"):
        persist_stage(
            tmp_path / "runs", tmp_path, "run_001", "topic_c", "brief_review_gauntlet", 1,
            "content/brief.md", "brief", {"artifact": "content/brief.md"}, valid_review("content/brief.md"),
        )


def test_persist_stage_rejects_invalid_gauntlet_review_contract(tmp_path):
    write_fixture(tmp_path)
    topic = load_and_select_topics(tmp_path / "content/backlog.md", tmp_path / "research/topics", "1")
    freeze_manifest(tmp_path / "runs", "run_001", "1", topic)
    with pytest.raises(ValueError, match="review is invalid"):
        persist_stage(
            tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
            "content/draft.md", "draft", {"ok": True}, {
                "decision": "approved", "coverage": 1.0, "criteria": {},
                "hard_failures": [], "feedback": [], "artifact": "content/draft.md",
            },
        )


def test_approval_stage_sets_terminal_current_stage(tmp_path):
    write_fixture(tmp_path)
    topics = load_and_select_topics(
        tmp_path / "content" / "backlog.md", tmp_path / "research" / "topics", "1"
    )
    freeze_manifest(tmp_path / "runs", "run_001", "1", topics)
    for index, stage in enumerate(CANONICAL_STAGES, start=1):
        artifact_path = f"content/{stage}.md"
        coverage = {"research-topic": 0.99, "humanize_review_1": 1.0}.get(stage, 1.0)
        review = valid_review(artifact_path)
        review["coverage"] = coverage
        persist_stage(
            tmp_path / "runs", tmp_path, "run_001", "topic_c", stage, index,
            artifact_path, stage, {"stage": stage, "artifact": artifact_path}, review,
        )
    state = yaml.safe_load((tmp_path / "runs/run_001/topics/topic_c/state.yaml").read_text())
    manifest = yaml.safe_load((tmp_path / "runs/run_001/manifest.yaml").read_text())
    assert state["current_stage"] is None
    assert manifest["queue"][0]["current_stage"] is None
    assert manifest["queue"][0]["status"] == "completed"
    assert manifest["metrics"]["reviewer_coverage"] == 0.999
    assert manifest["metrics"]["human_writing_conformity"] == 1.0
    assert manifest["metrics"]["cycles_per_stage"]["research-topic"] == 1
    assert manifest["metrics"]["time_to_approval"].startswith("PT")


def test_idempotency_rejects_adultered_review_even_when_file_exists(tmp_path):
    write_fixture(tmp_path)
    freeze_manifest(tmp_path / "runs", "run_001", "1", load_and_select_topics(
        tmp_path / "content/backlog.md", tmp_path / "research/topics", "1"
    ))
    artifact = "content/draft.md"
    result = {"artifact": "content/draft.md"}
    review = valid_review(artifact)
    persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                  artifact, "draft", result, review)
    adultered = dict(review)
    adultered["coverage"] = 0.99
    (tmp_path / "runs/run_001/topics/topic_c/reviews/cycle-01.yaml").write_text(yaml.safe_dump(adultered))
    with pytest.raises(ValueError, match="payload|event"):
        persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                      artifact, "changed", result, adultered)


def test_partial_recovery_rejects_existing_files_that_do_not_match_intent(tmp_path):
    write_fixture(tmp_path)
    freeze_manifest(tmp_path / "runs", "run_001", "1", load_and_select_topics(
        tmp_path / "content/backlog.md", tmp_path / "research/topics", "1"
    ))
    events_file = tmp_path / "runs/run_001/events.yaml"
    events_file.write_text(yaml.safe_dump({"contract_version": "1", "events": [{
        "event_id": "evt_0001", "phase": "intent",
        "idempotency_key": ["run_001", "topic_c", "research-topic", 1],
        "artifact_path": "content/draft.md",
        "result_path": "runs/run_001/topics/topic_c/results/research-topic-cycle-01.yaml",
        "review_path": "runs/run_001/topics/topic_c/reviews/cycle-01.yaml",
    }]}))
    (tmp_path / "content/draft.md").parent.mkdir(exist_ok=True)
    (tmp_path / "content/draft.md").write_text("old")
    with pytest.raises(ValueError, match="partial|intent"):
        persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                      "content/draft.md", "new", valid_result("content/draft.md"), valid_review("content/draft.md"))


def test_blocked_or_terminal_state_cannot_transition_and_blocked_stage_is_canonical(tmp_path):
    write_fixture(tmp_path)
    freeze_manifest(tmp_path / "runs", "run_001", "1", load_and_select_topics(
        tmp_path / "content/backlog.md", tmp_path / "research/topics", "1"
    ))
    state_file = state_path(tmp_path / "runs", "run_001", "topic_c")
    state_file.parent.mkdir(parents=True)
    state_file.write_text(yaml.safe_dump({
        "contract_version": "1", "run_id": "run_001", "topic_id": "topic_c",
        "status": "blocked", "current_stage": None, "completed_stages": [],
    }))
    with pytest.raises(ValueError, match="terminal|current_stage"):
        persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                      "content/draft.md", "draft", valid_result("content/draft.md"), valid_review("content/draft.md"))
    state_file.write_text(yaml.safe_dump({
        "contract_version": "1", "run_id": "run_001", "topic_id": "topic_c",
        "status": "completed", "current_stage": None, "completed_stages": CANONICAL_STAGES,
    }))
    with pytest.raises(ValueError, match="terminal"):
        continue_after_failure(tmp_path / "runs", tmp_path, "run_001", "topic_c", "failed")


def test_checkpoint_and_event_paths_and_ids_must_match_canonical_locations(tmp_path):
    artifact = tmp_path / "brief.md"
    artifact.write_text("brief")
    state = {
        "contract_version": "1", "run_id": "run", "topic_id": "topic",
        "completed_stages": ["research-topic"],
        "checkpoint": {
            "stage": "research-topic", "cycle": 1, "result": {"ok": True},
            "last_artifact": "brief.md", "result_path": "result.yaml",
            "input_fingerprint": "sha256:" + hashlib.sha256(b"brief").hexdigest(),
            "paths": ["brief.md", "result.yaml", "review.yaml"], "review_path": "review.yaml",
            "saved_at": "now",
        },
    }
    (tmp_path / "result.yaml").write_text(yaml.safe_dump({"ok": True}))
    (tmp_path / "review.yaml").write_text(yaml.safe_dump({"ok": True}))
    assert checkpoint_valid(state, tmp_path) is False


def test_incomplete_commit_event_does_not_change_metrics(tmp_path):
    manifest = {"queue": [], "metrics": {**DEFAULT_METRICS}}
    events = [{"phase": "commit", "stage": "research-topic", "cycle": 99,
               "review": {"coverage": 1.0}}]
    _update_metrics(manifest, events)
    assert manifest["metrics"]["cycles_per_stage"] == {}
    assert manifest["metrics"]["reviewer_coverage"] == 0.0


def test_persist_stage_rejects_quality_gate_failures(tmp_path):
    write_fixture(tmp_path)
    freeze_manifest(tmp_path / "runs", "run_001", "1", load_and_select_topics(
        tmp_path / "content/backlog.md", tmp_path / "research/topics", "1"
    ))
    review = valid_review("content/draft.md")
    review["coverage"] = 0.98
    with pytest.raises(ValueError, match="quality gate"):
        persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                      "content/draft.md", "draft", valid_result("content/draft.md"), review)


def test_manifest_rejects_frozen_queue_tampering(tmp_path):
    write_fixture(tmp_path)
    topics = load_and_select_topics(tmp_path / "content/backlog.md", tmp_path / "research/topics", "1")
    freeze_manifest(tmp_path / "runs", "run_001", "1", topics)
    manifest_path = tmp_path / "runs/run_001/manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest["queue"][0]["score"] = 1
    manifest_path.write_text(yaml.safe_dump(manifest))
    with pytest.raises(ValueError, match="frozen queue"):
        freeze_manifest(tmp_path / "runs", "run_001", "1", topics)


def test_metrics_use_only_canonical_commits_and_real_review_coverage(tmp_path):
    write_fixture(tmp_path)
    topics = load_and_select_topics(tmp_path / "content/backlog.md", tmp_path / "research/topics", "1")
    freeze_manifest(tmp_path / "runs", "run_001", "1", topics)
    persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                  "content/research.md", "research", {"artifact": "content/research.md"}, valid_review("content/research.md"))
    events_path_value = event_path(tmp_path / "runs", "run_001")
    events = yaml.safe_load(events_path_value.read_text())
    events["events"].append({"phase": "commit", "stage": "write-post", "cycle": 40,
                              "review": {"coverage": 0.0}})
    events_path_value.write_text(yaml.safe_dump(events))
    with pytest.raises(ValueError, match="event"):
        persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "brief_review_gauntlet", 1,
                      "content/brief.md", "brief", valid_result("content/brief.md"), valid_review("content/brief.md"))


def test_invalid_result_is_rejected_before_any_cycle_file_is_written(tmp_path):
    write_fixture(tmp_path)
    freeze_manifest(tmp_path / "runs", "run_001", "1", load_and_select_topics(
        tmp_path / "content/backlog.md", tmp_path / "research/topics", "1"
    ))
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    with pytest.raises(ValueError, match="result|artifact"):
        persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                      "content/draft.md", "draft", {"ok": True}, valid_review("content/draft.md"))
    assert sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*")) == before


def test_cycle_paths_reject_parent_segments_before_writing(tmp_path):
    write_fixture(tmp_path)
    freeze_manifest(tmp_path / "runs", "run_001", "1", load_and_select_topics(
        tmp_path / "content/backlog.md", tmp_path / "research/topics", "1"
    ))
    with pytest.raises(ValueError, match="path"):
        persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                      "content/dir/../draft.md", "draft",
                      {"artifact": "content/dir/../draft.md"},
                      valid_review("content/dir/../draft.md"))
    assert not (tmp_path / "content/draft.md").exists()


def test_intent_path_divergence_is_rejected_without_recovery_writes(tmp_path):
    write_fixture(tmp_path)
    freeze_manifest(tmp_path / "runs", "run_001", "1", load_and_select_topics(
        tmp_path / "content/backlog.md", tmp_path / "research/topics", "1"
    ))
    events_file = event_path(tmp_path / "runs", "run_001")
    events_file.write_text(yaml.safe_dump({"contract_version": "1", "events": [{
        "event_id": "evt_0001", "phase": "intent",
        "idempotency_key": ["run_001", "topic_c", "research-topic", 1],
        "artifact_path": "content/other.md",
        "result_path": "runs/run_001/topics/topic_c/results/research-topic-cycle-01.yaml",
        "review_path": "runs/run_001/topics/topic_c/reviews/cycle-01.yaml",
    }]}))
    with pytest.raises(ValueError, match="intent|path"):
        persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                      "content/draft.md", "draft", {"artifact": "content/draft.md"},
                      valid_review("content/draft.md"))
    assert not (tmp_path / "content/draft.md").exists()


def test_unknown_state_status_invalidates_checkpoint_and_blocks_writes(tmp_path):
    write_fixture(tmp_path)
    freeze_manifest(tmp_path / "runs", "run_001", "1", load_and_select_topics(
        tmp_path / "content/backlog.md", tmp_path / "research/topics", "1"
    ))
    state_file = state_path(tmp_path / "runs", "run_001", "topic_c")
    state_file.parent.mkdir(parents=True)
    state_file.write_text(yaml.safe_dump({
        "contract_version": "1", "run_id": "run_001", "topic_id": "topic_c",
        "status": "mystery", "current_stage": "research-topic", "completed_stages": [],
    }))
    with pytest.raises(ValueError, match="status"):
        persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                      "content/draft.md", "draft", {"artifact": "content/draft.md"},
                      valid_review("content/draft.md"))
    assert not (tmp_path / "content/draft.md").exists()


def test_commit_event_requires_canonical_id_timestamp_paths_and_passing_review(tmp_path):
    write_fixture(tmp_path)
    freeze_manifest(tmp_path / "runs", "run_001", "1", load_and_select_topics(
        tmp_path / "content/backlog.md", tmp_path / "research/topics", "1"
    ))
    persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                  "content/draft.md", "draft", {"artifact": "content/draft.md"},
                  valid_review("content/draft.md"))
    event = yaml.safe_load(event_path(tmp_path / "runs", "run_001").read_text())["events"][-1]
    assert _valid_commit_event(event)
    for field, value in (("event_id", "bad"), ("committed_at", "bad"),
                         ("review_path", "runs/other/topics/topic_c/reviews/cycle-01.yaml")):
        altered = dict(event)
        altered[field] = value
        assert _valid_commit_event(altered) is False
    altered = dict(event)
    altered["review"] = {**event["review"], "coverage": 0.5}
    assert _valid_commit_event(altered) is False


def test_human_metrics_ignore_incomplete_commit_events(tmp_path):
    manifest = {"queue": [], "metrics": {**DEFAULT_METRICS}}
    events = [{"phase": "commit", "stage": "humanize_review_1", "cycle": 1,
               "review": {"coverage": 0.0}}]
    _update_metrics(manifest, events)
    assert manifest["metrics"]["human_writing_conformity"] == 0.0


def test_checkpoint_reapplies_complete_review_gate(tmp_path):
    write_fixture(tmp_path)
    freeze_manifest(tmp_path / "runs", "run_001", "1", load_and_select_topics(
        tmp_path / "content/backlog.md", tmp_path / "research/topics", "1"
    ))
    persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                  "content/draft.md", "draft", {"artifact": "content/draft.md"},
                  valid_review("content/draft.md"))
    state_file = state_path(tmp_path / "runs", "run_001", "topic_c")
    state = yaml.safe_load(state_file.read_text())
    state["checkpoint"]["review"]["coverage"] = 0.98
    assert checkpoint_valid(state, tmp_path) is False


def test_checkpoint_rejects_hard_failure_low_criterion_and_unresolved_feedback(tmp_path):
    write_fixture(tmp_path)
    freeze_manifest(tmp_path / "runs", "run_001", "1", load_and_select_topics(
        tmp_path / "content/backlog.md", tmp_path / "research/topics", "1"
    ))
    persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                  "content/draft.md", "draft", valid_result("content/draft.md"),
                  valid_review("content/draft.md"))
    state_file = state_path(tmp_path / "runs", "run_001", "topic_c")
    state = yaml.safe_load(state_file.read_text())
    review = state["checkpoint"]["review"]
    for change in (
        {"hard_failures": ["critical"]},
        {"criteria": {**review["criteria"], "clareza": 8}},
        {"feedback": [{"criterion": "clareza", "message": "resolve"}]},
    ):
        altered = {**review, **change}
        state["checkpoint"]["review"] = altered
        assert checkpoint_valid(state, tmp_path) is False


def test_invalid_committed_cycle_does_not_raise_cycles_metric(tmp_path):
    manifest = {"queue": [], "metrics": {**DEFAULT_METRICS}}
    valid = {
        "event_id": "evt_0001", "phase": "commit",
        "idempotency_key": ["run_001", "topic_c", "research-topic", 1],
        "stage": "research-topic", "cycle": 1,
        "artifact_path": "content/draft.md",
        "result_path": "runs/run_001/topics/topic_c/results/research-topic-cycle-01.yaml",
        "review_path": "runs/run_001/topics/topic_c/reviews/cycle-01.yaml",
        "committed_at": "2026-09-01T10:00:00+00:00",
        "result": {"artifact": "content/draft.md"},
        "review": valid_review("content/draft.md"),
    }
    malformed = {**valid, "cycle": 99, "stage": "research-topic"}
    _update_metrics(manifest, [valid, malformed])
    assert manifest["metrics"]["cycles_per_stage"]["research-topic"] == 1


def test_commit_event_rejects_divergent_result_artifact_and_preserves_metrics(tmp_path):
    write_fixture(tmp_path)
    freeze_manifest(tmp_path / "runs", "run_001", "1", load_and_select_topics(
        tmp_path / "content/backlog.md", tmp_path / "research/topics", "1"
    ))
    persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                  "content/draft.md", "draft", valid_result("content/draft.md"),
                  valid_review("content/draft.md"))
    event = yaml.safe_load(event_path(tmp_path / "runs", "run_001").read_text())["events"][-1]
    altered = {**event, "result": {"artifact": "content/other.md"}}
    manifest = yaml.safe_load((tmp_path / "runs/run_001/manifest.yaml").read_text())
    metrics_before = manifest["metrics"].copy()
    _update_metrics(manifest, [event, altered])
    assert _valid_commit_event(altered, tmp_path) is False
    assert manifest["metrics"] == metrics_before


def test_commit_event_with_root_requires_existing_regular_nonempty_review(tmp_path):
    write_fixture(tmp_path)
    freeze_manifest(tmp_path / "runs", "run_001", "1", load_and_select_topics(
        tmp_path / "content/backlog.md", tmp_path / "research/topics", "1"
    ))
    persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                  "content/draft.md", "draft", valid_result("content/draft.md"),
                  valid_review("content/draft.md"))
    events = yaml.safe_load(event_path(tmp_path / "runs", "run_001").read_text())["events"]
    event = events[-1]
    review_file = tmp_path / event["review_path"]
    review_file.unlink()
    assert _valid_commit_event(event, tmp_path) is False
    review_file.write_text("")
    assert _valid_commit_event(event, tmp_path) is False


def test_checkpoint_result_non_dict_returns_false_and_preserves_state(tmp_path):
    write_fixture(tmp_path)
    freeze_manifest(tmp_path / "runs", "run_001", "1", load_and_select_topics(
        tmp_path / "content/backlog.md", tmp_path / "research/topics", "1"
    ))
    persist_stage(tmp_path / "runs", tmp_path, "run_001", "topic_c", "research-topic", 1,
                  "content/draft.md", "draft", valid_result("content/draft.md"),
                  valid_review("content/draft.md"))
    state_file = state_path(tmp_path / "runs", "run_001", "topic_c")
    original = state_file.read_bytes()
    state = yaml.safe_load(original)
    for result in (None, [], "invalid"):
        state["checkpoint"]["result"] = result
        assert checkpoint_valid(state, tmp_path) is False
        assert state_file.read_bytes() == original
