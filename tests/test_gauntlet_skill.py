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

    result = run_gauntlet(executor, reviewer)

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

    result = run_gauntlet(executor, lambda artifact, feedback: next(reviews))

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

    result = run_gauntlet(executor, reviewer)

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
