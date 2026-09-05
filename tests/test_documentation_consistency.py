import json
from pathlib import Path

import pytest
import yaml

from editorial_batch import CANONICAL_STAGES, freeze_manifest, load_and_select_topics, persist_stage
from gauntlet_loop import NORMATIVE_CRITERIA, run_gauntlet


def _topics_fixture(root):
    (root / "content").mkdir()
    (root / "research/topics").mkdir(parents=True)
    (root / "content/backlog.md").write_text("topic_a 81 ready_for_research")
    (root / "research/topics/topics_20260901.yaml").write_text(yaml.safe_dump({
        "topics": [{"topic_id": "topic_a", "score": 81, "status": "ready_for_research"}]
    }))


def _review(artifact):
    return {
        "decision": "approved",
        "coverage": 1.0,
        "criteria": {criterion: 10 for criterion in NORMATIVE_CRITERIA},
        "hard_failures": [],
        "feedback": [],
        "artifact": artifact,
    }


def test_manifest_persists_canonical_metrics(tmp_path):
    _topics_fixture(tmp_path)
    topic = load_and_select_topics(
        tmp_path / "content/backlog.md", tmp_path / "research/topics", "1"
    )
    manifest = freeze_manifest(tmp_path / "runs", "run-1", "1", topic)

    assert manifest["metrics"] == {
        "queue_size": 1,
        "completed": 0,
        "blocked": 0,
        "cycles_per_stage": {},
        "reviewer_coverage": 0.0,
        "human_writing_conformity": 0.0,
        "time_to_approval": None,
    }
    saved = yaml.safe_load((tmp_path / "runs/run-1/manifest.yaml").read_text())
    assert saved["metrics"] == manifest["metrics"]


def test_resume_rejects_divergent_artifact_result_review_or_fingerprint(tmp_path):
    _topics_fixture(tmp_path)
    topic = load_and_select_topics(tmp_path / "content/backlog.md", tmp_path / "research/topics", "1")
    freeze_manifest(tmp_path / "runs", "run-1", "1", topic)
    artifact = "content/draft.md"
    result = {"decision": "approved", "artifact": artifact}
    review = _review(artifact)
    persist_stage(tmp_path / "runs", tmp_path, "run-1", "topic_a", "research-topic", 1,
                  artifact, "original", result, review)

    (tmp_path / artifact).write_text("tampered")
    with pytest.raises(ValueError, match="divergent"):
        persist_stage(tmp_path / "runs", tmp_path, "run-1", "topic_a", "research-topic", 1,
                      artifact, "original", result, review)

    blocked = persist_stage(
        tmp_path / "runs", tmp_path, "run-1", "topic_a", "research-topic", 1,
        artifact, "original", {**result, "decision": "feedback"}, review,
    )
    assert blocked["status"] == "blocked"
    assert blocked["failure_reasons"][0]["code"] == "intent_payload_divergence"


def test_corrupt_gauntlet_events_and_state_fail_closed(tmp_path):
    artifact = tmp_path / "draft.md"
    artifact.write_text("draft")
    events_path = tmp_path / "events.yaml"
    events_path.write_text("{broken")
    result = run_gauntlet(lambda feedback: "draft.md", lambda path, feedback: _review(path),
                          artifact_path="draft.md", workspace_root=tmp_path, persistence_dir=tmp_path)
    assert result["status"] == "blocked"
    assert result["failure_reasons"] == ["persistence error: events.yaml is corrupt"]
    assert events_path.read_text() == "{broken"

    events_path.unlink()
    state_path = tmp_path / "state.yaml"
    state_path.write_text("{broken")
    result = run_gauntlet(lambda feedback: "draft.md", lambda path, feedback: _review(path),
                          artifact_path="draft.md", workspace_root=tmp_path, persistence_dir=tmp_path)
    assert result["status"] == "blocked"
    assert result["failure_reasons"] == ["persistence error: state.yaml is corrupt"]
    assert state_path.read_text() == "{broken"


def test_resume_requires_matching_review_and_artifact_fingerprint(tmp_path):
    artifact = tmp_path / "draft.md"
    artifact.write_text("draft")
    run_gauntlet(lambda feedback: "draft.md", lambda path, feedback: _review(path),
                 artifact_path="draft.md", workspace_root=tmp_path, persistence_dir=tmp_path)
    state_path = tmp_path / "state.yaml"
    state = json.loads(state_path.read_text())
    state["artifact_fingerprint"] = "sha256:invalid"
    state_path.write_text(json.dumps(state))

    result = run_gauntlet(lambda feedback: "draft.md", lambda path, feedback: _review(path),
                          artifact_path="draft.md", workspace_root=tmp_path, persistence_dir=tmp_path)
    assert result["status"] == "blocked"
    assert "state fingerprint is divergent" in result["failure_reasons"]


def test_reviews_are_persisted_and_scheduling_is_not_a_batch_stage(tmp_path):
    artifact = tmp_path / "draft.md"
    artifact.write_text("draft")
    run_gauntlet(lambda feedback: "draft.md", lambda path, feedback: _review(path),
                 artifact_path="draft.md", workspace_root=tmp_path, persistence_dir=tmp_path)

    review = json.loads((tmp_path / "cycle-01.yaml").read_text())["review"]
    assert review["artifact"] == "draft.md"
    assert "publicar-linkedin" not in Path("editorial_batch.py").read_text()
    assert "publicar-linkedin" not in Path("gauntlet_loop.py").read_text()
    docs = "\n".join(Path(path).read_text() for path in (
        "README.md", ".agents/skills/run-editorial-batch/SKILL.md", "docs/roadmap.md"
    ))
    assert "agendamento permanece separado" in docs.lower() or "scheduling remains outside" in docs.lower()
    assert "human_writing_conformity" in docs
    assert "time_to_approval" in docs
    assert "human-writing_conformity" not in docs


def test_manifest_metrics_are_aggregated_by_the_persistence_runtime(tmp_path):
    _topics_fixture(tmp_path)
    topic = load_and_select_topics(tmp_path / "content/backlog.md", tmp_path / "research/topics", "1")
    freeze_manifest(tmp_path / "runs", "run-1", "1", topic)
    for cycle, stage in enumerate(CANONICAL_STAGES, start=1):
        artifact = f"content/{stage}.md"
        persist_stage(
            tmp_path / "runs", tmp_path, "run-1", "topic_a", stage, cycle,
            artifact, stage, {"stage": stage, "artifact": artifact}, _review(artifact),
        )

    manifest = yaml.safe_load((tmp_path / "runs/run-1/manifest.yaml").read_text())
    assert manifest["metrics"]["reviewer_coverage"] == 1.0
    assert manifest["metrics"]["human_writing_conformity"] == 1.0
    assert manifest["metrics"]["cycles_per_stage"] == {
        stage: cycle for cycle, stage in enumerate(CANONICAL_STAGES, start=1)
    }
    assert manifest["metrics"]["time_to_approval"].startswith("PT")
