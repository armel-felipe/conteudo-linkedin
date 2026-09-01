from pathlib import Path
import math
import json
import inspect

import pytest

from gauntlet_loop import NORMATIVE_CRITERIA, run_gauntlet, validate_review


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


def review(*, coverage=1.0, criteria=None, decision="approved", hard_failures=None, feedback=None, artifact="mapa.md"):
    if criteria is None:
        criteria = {name: 10 for name in NORMATIVE_CRITERIA}
    elif set(criteria) == {"clarity"}:
        clarity_score = criteria["clarity"]
        criteria = {name: 10 for name in NORMATIVE_CRITERIA}
        criteria["clareza"] = clarity_score
    if feedback:
        feedback = [
            (
                {**item, "criterion": "clareza" if item.get("criterion") == "clarity" else item.get("criterion")}
                if isinstance(item, dict)
                else item
            )
            for item in feedback
        ]
    return {
        "decision": decision,
        "coverage": coverage,
        "criteria": criteria,
        "hard_failures": [] if hard_failures is None else hard_failures,
        "feedback": [] if feedback is None else feedback,
        "artifact": artifact,
    }


def test_run_gauntlet_retries_quality_feedback_five_times_without_sixth_call():
    executor_calls = []
    reviewer_calls = []

    def executor(feedback):
        executor_calls.append(feedback)
        return "mapa.md"

    def reviewer(artifact, feedback):
        reviewer_calls.append((artifact, feedback))
        return review(
            coverage=0.99,
            criteria={"clarity": 8},
            decision="approved",
            feedback=[{"criterion": "clarity", "message": "Make the opening specific."}],
        )

    result = run_gauntlet(executor, reviewer, artifact_path="mapa.md")

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
        return "mapa.md"

    result = run_gauntlet(executor, lambda artifact, feedback: next(reviews), artifact_path="mapa.md")

    assert result["status"] == "approved"
    assert result["cycle_count"] == 2
    assert seen_feedback[1] == [{"criterion": "clareza", "message": "Use one concrete example."}]


def test_run_gauntlet_stops_on_hard_failure_without_retry():
    calls = []

    def executor(feedback):
        calls.append("executor")
        return "mapa.md"

    def reviewer(artifact, feedback):
        calls.append("reviewer")
        return review(hard_failures=["evidence missing"])

    result = run_gauntlet(executor, reviewer, artifact_path="mapa.md")

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
    assert quality == {"valid": True, "terminal": False, "errors": [], "quality_feedback": ["clareza"]}


def test_schema_is_strict_and_feedback_is_criterion_associated():
    schema = json.loads(Path("docs/schemas/gauntlet-review.json").read_text())
    assert schema["additionalProperties"] is False
    assert schema["properties"]["coverage"]["minimum"] == 0
    assert schema["properties"]["coverage"]["maximum"] == 1
    assert schema["properties"]["criteria"]["minProperties"] == 14
    assert schema["properties"]["criteria"]["additionalProperties"]["type"] == "number"
    assert schema["properties"]["feedback"]["items"]["required"] == ["criterion", "message"]


def test_run_gauntlet_rejects_absolute_or_unexpected_artifacts_before_reviewer():
    reviewer_calls = []

    def reviewer(artifact, feedback):
        reviewer_calls.append(artifact)
        return review()

    absolute = run_gauntlet(lambda feedback: "/tmp/mapa.md", reviewer, artifact_path="mapa.md")
    different = run_gauntlet(lambda feedback: "other.md", reviewer, artifact_path="mapa.md")

    assert absolute["status"] == different["status"] == "blocked"
    assert reviewer_calls == []
    assert all("artifact" in reason for result in (absolute, different) for reason in result["failure_reasons"])


def test_blocked_after_five_cycles_contains_complete_terminal_payload():
    def executor(feedback):
        return "mapa.md"

    def reviewer(artifact, feedback):
        return review(
            coverage=0.99,
            criteria={"clarity": 8},
            feedback=[{"criterion": "clarity", "message": "Use a concrete example."}],
        )

    result = run_gauntlet(executor, reviewer, artifact_path="mapa.md")

    assert result["status"] == "blocked"
    assert result["cycles"] == 5
    assert result["cycle_count"] == 5
    assert result["failed_criteria"] == ["clareza"]
    assert result["last_artifact"] == "mapa.md"
    assert result["last_review"]["artifact"] == "mapa.md"
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
        return "mapa.md"

    def reviewer(artifact, feedback):
        calls["reviewer"] += 1
        return next(reviews)

    first = run_gauntlet(
        executor,
        reviewer,
        artifact_path="mapa.md",
        persistence_dir=tmp_path,
        run_id="run-1",
    )
    second = run_gauntlet(
        executor,
        reviewer,
        artifact_path="mapa.md",
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
        return "mapa.md"

    def reviewer(artifact, feedback):
        observations.append(("reviewer", id(feedback), list(feedback)))
        return next(reviews)

    run_gauntlet(executor, reviewer, artifact_path="mapa.md")

    assert observations[0][0] == "executor"
    assert observations[1] == ("reviewer", observations[1][1], [])
    assert observations[0][1] != observations[1][1]
    assert observations[2][0] == "executor"
    assert observations[3][0] == "reviewer"
    assert observations[3][2] == [{"criterion": "clareza", "message": "Be specific."}]


def test_deterministic_checks_require_existing_regular_nonempty_artifact(tmp_path):
    reviewer_calls = []
    empty = tmp_path / "empty.md"
    empty.write_text("")

    def reviewer(artifact, feedback):
        reviewer_calls.append(artifact)
        return review(artifact="draft.md")

    missing = run_gauntlet(
        lambda feedback: "missing.md", reviewer, artifact_path="missing.md", workspace_root=tmp_path
    )
    empty_result = run_gauntlet(
        lambda feedback: "empty.md", reviewer, artifact_path="empty.md", workspace_root=tmp_path
    )

    assert missing["status"] == empty_result["status"] == "blocked"
    assert missing["failure_reasons"] == ["artifact missing"]
    assert empty_result["failure_reasons"] == ["artifact empty"]
    assert reviewer_calls == []


def test_artifact_must_be_inside_root_and_rejects_windows_paths(tmp_path):
    (tmp_path / "draft.md").write_text("draft")
    reviewer = lambda artifact, feedback: review(artifact="draft.md")

    outside = run_gauntlet(
        lambda feedback: "../draft.md", reviewer, artifact_path="../draft.md", workspace_root=tmp_path
    )
    windows = run_gauntlet(
        lambda feedback: r"draft\file.md", reviewer, artifact_path=r"draft\file.md", workspace_root=tmp_path
    )
    drive = run_gauntlet(
        lambda feedback: "C:/draft.md", reviewer, artifact_path="C:/draft.md", workspace_root=tmp_path
    )

    assert outside["status"] == windows["status"] == drive["status"] == "blocked"
    assert "root" in outside["failure_reasons"][0]
    assert "path" in windows["failure_reasons"][0]


def test_executor_and_reviewer_must_be_distinct_callbacks():
    def callback(*args):
        return "mapa.md"

    result = run_gauntlet(callback, callback, artifact_path="mapa.md")

    assert result["status"] == "blocked"
    assert "distinct" in result["failure_reasons"][0]


def test_partial_cycle_with_divergent_payload_fails_without_overwriting(tmp_path):
    original = {"idempotency_key": ["run-1", "mapa.md", 1], "review": {"old": True}}
    cycle = tmp_path / "cycle-01.yaml"
    cycle.write_text(json.dumps(original))

    result = run_gauntlet(
        lambda feedback: "mapa.md",
        lambda artifact, feedback: review(),
        artifact_path="mapa.md",
        persistence_dir=tmp_path,
        run_id="run-1",
    )

    assert result["status"] == "blocked"
    assert "divergent" in result["failure_reasons"][0]
    assert json.loads(cycle.read_text()) == original


def test_divergent_existing_terminal_state_fails_closed_without_reusing_it(tmp_path):
    state = {"status": "blocked", "cycles": 5, "last_artifact": "other.md"}
    state_path = tmp_path / "state.yaml"
    state_path.write_text(json.dumps(state))
    calls = []

    result = run_gauntlet(
        lambda feedback: calls.append("executor") or "mapa.md",
        lambda artifact, feedback: calls.append("reviewer") or review(),
        artifact_path="mapa.md",
        persistence_dir=tmp_path,
        run_id="run-1",
    )

    assert result["status"] == "blocked"
    assert "state" in result["failure_reasons"][0]
    assert calls == []
    assert json.loads(state_path.read_text()) == state


def test_run_gauntlet_signature_exposes_artifact_persistence_and_run_identity():
    parameters = inspect.signature(run_gauntlet).parameters

    assert parameters["artifact_path"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["persistence_dir"].default is None
    assert parameters["run_id"].default == "run"
    assert parameters["workspace_root"].default is None
