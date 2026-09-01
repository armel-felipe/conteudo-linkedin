import json
from pathlib import Path

import yaml

from gauntlet_loop import NORMATIVE_CRITERIA


def test_run_schema_documents_exist_and_have_required_fields():
    run = yaml.safe_load(Path("docs/schemas/editorial-run.yaml").read_text())
    assert {"run_id", "created_at", "selection", "queue", "topics"} <= set(run)
    assert run["queue"][0]["topic_id"] == "topic_YYYYMMDD_NN"
    assert run["queue"][0]["status"] == "queued"
    assert run["queue"][0]["current_stage"] == "research-topic"


def test_gauntlet_review_schema_has_required_keys_and_decision_enum():
    review = json.loads(Path("docs/schemas/gauntlet-review.json").read_text())
    assert set(review["required"]) >= {
        "decision",
        "coverage",
        "criteria",
        "hard_failures",
        "feedback",
        "artifact",
    }
    assert review["properties"]["decision"]["enum"] == ["approved", "feedback"]
    assert review["properties"]["feedback"]["type"] == "array"
    assert review["properties"]["criteria"]["propertyNames"]["enum"] == list(NORMATIVE_CRITERIA)


def test_batch_skill_documents_canonical_result_and_review_paths_and_criteria():
    skill = Path(".agents/skills/run-editorial-batch/SKILL.md").read_text()
    assert "result_path: runs/run_20260901_001/topics/topic_c/results/brief_review_gauntlet-cycle-01.yaml" in skill
    assert "result_path: runs/run_20260901_001/topics/topic_c/reviews/cycle-01.yaml" not in skill
    assert "  evidence: 9" not in skill
    assert "  author_connection: 10" not in skill
    for criterion in NORMATIVE_CRITERIA:
        assert criterion in skill


def test_runtime_runs_are_ignored_but_keep_file_is_tracked():
    gitignore = Path(".gitignore").read_text()
    assert "runs/*" in gitignore
    assert Path("runs/.gitkeep").exists()
