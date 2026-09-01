import re
from pathlib import Path

import yaml


SKILL = Path(".agents/skills/run-editorial-batch/SKILL.md").read_text()


def _yaml_example(name):
    match = re.search(
        rf"<!-- {name} -->\n```yaml\n(.*?)\n```",
        SKILL,
        flags=re.DOTALL,
    )
    assert match, f"missing YAML example: {name}"
    return yaml.safe_load(match.group(1))


def test_batch_skill_documents_selection_and_failure_policy():
    assert all(option in SKILL for option in ("--topics 1", "--topics N", "--topics all"))
    assert "--topics topic_a,topic_b" in SKILL


def test_selection_filters_ready_topics_and_orders_by_score_with_topic_tiebreaker():
    selection = _yaml_example("selection-example")
    assert selection["eligible_topic_ids"] == ["topic_c", "topic_d", "topic_a"]
    assert selection["ignored"]["topic_b"] == "candidate"


def test_manifest_and_state_examples_freeze_queue_and_define_valid_checkpoint():
    manifest = _yaml_example("manifest-example")
    state = _yaml_example("state-example")
    assert manifest["path"] == "runs/run_20260901_001/manifest.yaml"
    assert manifest["queue_frozen"] is True
    assert [item["topic_id"] for item in manifest["queue"]] == ["topic_c", "topic_d", "topic_a"]
    assert state["path"] == "runs/run_20260901_001/topics/topic_c/state.yaml"
    assert state["checkpoint"]["valid"] is True
    assert state["checkpoint"]["completed_stages"] == ["research-topic", "brief-review-gauntlet"]


def test_stage_sequence_is_sequential_and_excludes_publication():
    stages = _yaml_example("stage-sequence-example")["stages"]
    assert stages == [
        "research-topic",
        "brief review Gauntlet",
        "write-post",
        "critique-post",
        "correction Gauntlet",
        "escrita-humana 1",
        "review 1",
        "escrita-humana 2",
        "review 2",
        "approval humana",
    ]
    assert "publicar-linkedin" not in stages


def test_failed_topic_is_blocked_and_next_topic_continues():
    failure = _yaml_example("failure-example")
    assert failure["queue"] == [
        {"topic_id": "topic_a", "status": "blocked"},
        {"topic_id": "topic_b", "status": "completed"},
    ]
    assert failure["execution_order"] == ["topic_a", "topic_b"]
