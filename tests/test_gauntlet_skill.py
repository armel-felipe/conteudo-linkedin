from pathlib import Path
import math
import json

import pytest

from gauntlet_loop import run_gauntlet, validate_review


SKILL = Path(".agents/skills/gauntlet-loop/SKILL.md")


def test_gauntlet_defines_five_round_limit_and_hard_gate():
    text = SKILL.read_text()
    assert "5 rodadas" in text
    assert "99%" in text
    assert "9/10" in text
    assert "executor" in text and "revisor" in text


def test_gauntlet_documents_isolated_cycle_and_structured_review_contract():
    text = SKILL.read_text()
    assert "cycle-start" in text
    assert "executor" in text
    assert "deterministic checks" in text
    assert "fresh reviewer" in text
    assert "structured result" in text
    assert "valid JSON" in text
    assert "task" in text


def test_gauntlet_documents_fail_closed_inputs_feedback_and_terminal_block():
    text = SKILL.read_text()
    assert "fail-closed" in text
    assert "missing artifact" in text
    assert "failed validation" in text
    assert "complete feedback" in text
    assert "blocked" in text
    assert "failure reasons" in text
    assert "failed criteria" in text
    assert "last artifact" in text
    assert "cycle count" in text
    assert "caller" in text


def test_quality_gate_returns_feedback_and_retries_instead_of_blocking():
    text = SKILL.read_text().lower()
    assert "coverage <=99%" in text
    assert "criteria <9/10" in text
    assert "feedback" in text
    assert "nao bloqueia" in text
    assert "cada criterio" in text


def test_strict_json_contract_defines_root_types_and_bounds():
    text = SKILL.read_text().lower()
    required_phrases = (
        "objeto raiz",
        "tipos corretos",
        "coverage finito",
        "entre 0 e 1",
        "criteria objeto",
        "numeros 0-10",
        "hard_failures",
        "feedback listas",
        "artifact string nao vazia",
        "decision enum",
    )
    for phrase in required_phrases:
        assert phrase in text


def test_retry_limit_and_terminal_categories_are_explicitly_distinguished():
    text = SKILL.read_text().lower()
    assert "ate 5" in text
    assert "sem sexta rodada" in text
    assert "falha estrutural" in text
    assert "hard failure" in text
    assert "json invalido" in text
    assert "executor/revisor indisponivel" in text
    assert "artifact ausente" in text
    assert "coverage <=99%" in text
    assert "criteria <9/10" in text


def review(*, coverage=1.0, criteria=None, decision="approved", hard_failures=None, feedback=None):
    return {
        "decision": decision,
        "coverage": coverage,
        "criteria": {"clarity": 10} if criteria is None else criteria,
        "hard_failures": [] if hard_failures is None else hard_failures,
        "feedback": [] if feedback is None else feedback,
        "artifact": "draft.md",
    }


def test_run_gauntlet_retries_quality_feedback_five_times_without_sixth_call():
    executor_calls = []
    reviewer_calls = []

    def executor(feedback):
        executor_calls.append(feedback)
        return "draft.md"

    def reviewer(artifact, feedback):
        reviewer_calls.append((artifact, feedback))
        return review(
            coverage=0.99,
            criteria={"clarity": 8},
            decision="approved",
            feedback=[{"criterion": "clarity", "message": "Make the opening specific."}],
        )

    result = run_gauntlet(executor, reviewer, artifact_path="draft.md")

    assert result["status"] == "blocked"
    assert result["cycle_count"] == 5
    assert len(executor_calls) == len(reviewer_calls) == 5
    assert len(reviewer_calls) != 6
    assert all(call[1] for call in reviewer_calls[1:])


def test_run_gauntlet_approves_after_quality_retry_and_passes_feedback():
    seen_feedback = []
    reviews = iter([
        review(
            coverage=0.99,
            criteria={"clarity": 8},
            decision="feedback",
            feedback=[{"criterion": "clarity", "message": "Use one concrete example."}],
        ),
        review(),
    ])

    def executor(feedback):
        seen_feedback.append(feedback)
        return "draft.md"

    result = run_gauntlet(executor, lambda artifact, feedback: next(reviews), artifact_path="draft.md")

    assert result["status"] == "approved"
    assert result["cycle_count"] == 2
    assert seen_feedback[1] == [{"criterion": "clarity", "message": "Use one concrete example."}]


def test_run_gauntlet_stops_on_hard_failure_without_retry():
    calls = []

    def executor(feedback):
        calls.append("executor")
        return "draft.md"

    def reviewer(artifact, feedback):
        calls.append("reviewer")
        return review(hard_failures=["evidence missing"])

    result = run_gauntlet(executor, reviewer, artifact_path="draft.md")

    assert result["status"] == "blocked"
    assert result["cycle_count"] == 1
    assert calls == ["executor", "reviewer"]


@pytest.mark.parametrize(
    "bad_review",
    [
        [],
        "not json",
        {"decision": "approved"},
        review(coverage=True),
        review(coverage=math.nan),
        review(coverage=math.inf),
        review(coverage=-0.01),
        review(coverage=1.01),
        review(criteria={}),
        review(criteria={"clarity": True}),
        review(criteria={"clarity": 11}),
        review(feedback=["unassociated feedback"]),
        {**review(), "extra": True},
    ],
)
def test_validate_review_rejects_invalid_json_root_types_values_and_extra_fields(bad_review):
    validation = validate_review(bad_review)
    assert validation["valid"] is False
    assert validation["terminal"] is True
    assert validation["errors"]


def test_validate_review_accepts_strict_review_and_quality_failure_is_not_terminal():
    quality = validate_review(
        review(
            coverage=0.99,
            criteria={"clarity": 8},
            feedback=[{"criterion": "clarity", "message": "Add a concrete example."}],
        )
    )
    assert quality == {"valid": True, "terminal": False, "errors": [], "quality_feedback": ["clarity"]}


def test_schema_is_strict_and_feedback_is_criterion_associated():
    schema = json.loads(Path("docs/schemas/gauntlet-review.json").read_text())
    assert schema["additionalProperties"] is False
    assert schema["properties"]["coverage"]["minimum"] == 0
    assert schema["properties"]["coverage"]["maximum"] == 1
    assert schema["properties"]["criteria"]["minProperties"] == 1
    assert schema["properties"]["criteria"]["additionalProperties"]["type"] == "number"
    assert schema["properties"]["feedback"]["items"]["required"] == ["criterion", "message"]


def test_run_gauntlet_rejects_absolute_or_unexpected_artifacts_before_reviewer():
    reviewer_calls = []

    def reviewer(artifact, feedback):
        reviewer_calls.append(artifact)
        return review()

    absolute = run_gauntlet(lambda feedback: "/tmp/draft.md", reviewer, artifact_path="draft.md")
    different = run_gauntlet(lambda feedback: "other.md", reviewer, artifact_path="draft.md")

    assert absolute["status"] == different["status"] == "blocked"
    assert reviewer_calls == []
    assert all("artifact" in reason for result in (absolute, different) for reason in result["failure_reasons"])


def test_blocked_after_five_cycles_contains_complete_terminal_payload():
    def executor(feedback):
        return "draft.md"

    def reviewer(artifact, feedback):
        return review(
            coverage=0.99,
            criteria={"clarity": 8},
            feedback=[{"criterion": "clarity", "message": "Use a concrete example."}],
        )

    result = run_gauntlet(executor, reviewer, artifact_path="draft.md")

    assert result["status"] == "blocked"
    assert result["cycles"] == 5
    assert result["cycle_count"] == 5
    assert result["failed_criteria"] == ["clarity"]
    assert result["last_artifact"] == "draft.md"
    assert result["last_review"]["artifact"] == "draft.md"
    assert result["feedback"] == result["last_review"]["feedback"]


def test_run_gauntlet_persists_cycles_events_state_atomically_and_idempotently(tmp_path):
    calls = {"executor": 0, "reviewer": 0}
    reviews = iter([
        review(
            coverage=0.99,
            criteria={"clarity": 8},
            decision="feedback",
            feedback=[{"criterion": "clarity", "message": "Add evidence."}],
        ),
        review(),
    ])

    def executor(feedback):
        calls["executor"] += 1
        return "draft.md"

    def reviewer(artifact, feedback):
        calls["reviewer"] += 1
        return next(reviews)

    first = run_gauntlet(
        executor,
        reviewer,
        artifact_path="draft.md",
        persistence_dir=tmp_path,
        run_id="run-1",
    )
    second = run_gauntlet(
        executor,
        reviewer,
        artifact_path="draft.md",
        persistence_dir=tmp_path,
        run_id="run-1",
    )

    assert first == second
    assert calls == {"executor": 2, "reviewer": 2}
    assert (tmp_path / "cycle-01.yaml").exists()
    assert (tmp_path / "cycle-02.yaml").exists()
    assert (tmp_path / "events.yaml").exists()
    assert (tmp_path / "state.yaml").exists()
    events = json.loads((tmp_path / "events.yaml").read_text())
    assert [event["type"] for event in events] == [
        "cycle-start", "deterministic-checks", "review",
        "cycle-start", "deterministic-checks", "review",
    ]
    assert len({tuple(event["idempotency_key"]) for event in events}) == len(events)


def test_callbacks_receive_separate_contexts_and_checks_precede_reviewer():
    observations = []
    reviews = iter([
        review(
            coverage=0.99,
            criteria={"clarity": 8},
            feedback=[{"criterion": "clarity", "message": "Be specific."}],
        ),
        review(),
    ])

    def executor(feedback):
        observations.append(("executor", id(feedback), list(feedback)))
        feedback.append({"criterion": "mutated", "message": "must not leak"})
        return "draft.md"

    def reviewer(artifact, feedback):
        observations.append(("reviewer", id(feedback), list(feedback)))
        return next(reviews)

    run_gauntlet(executor, reviewer, artifact_path="draft.md")

    assert observations[0][0] == "executor"
    assert observations[1] == ("reviewer", observations[1][1], [])
    assert observations[0][1] != observations[1][1]
    assert observations[2][0] == "executor"
    assert observations[3][0] == "reviewer"
    assert observations[3][2] == [{"criterion": "clarity", "message": "Be specific."}]
