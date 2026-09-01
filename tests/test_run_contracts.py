import json
from pathlib import Path

import yaml


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


def test_runtime_runs_are_ignored_but_keep_file_is_tracked():
    gitignore = Path(".gitignore").read_text()
    assert "runs/*" in gitignore
    assert Path("runs/.gitkeep").exists()
