"""Small, deterministic execution contract for the editorial Gauntlet."""

import math
from numbers import Real


REQUIRED_FIELDS = {"decision", "coverage", "criteria", "hard_failures", "feedback", "artifact"}
DECISIONS = {"approved", "feedback"}


def _number(value):
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)


def validate_review(review):
    """Return strict validation details without coercing reviewer output."""
    errors = []
    quality_feedback = []
    if not isinstance(review, dict):
        return {"valid": False, "terminal": True, "errors": ["root must be an object"]}

    if set(review) != REQUIRED_FIELDS:
        errors.append("fields must match the review contract exactly")

    if not isinstance(review.get("decision"), str) or review.get("decision") not in DECISIONS:
        errors.append("decision must be approved or feedback")

    coverage = review.get("coverage")
    if not _number(coverage) or not 0 <= coverage <= 1:
        errors.append("coverage must be finite and between 0 and 1")

    criteria = review.get("criteria")
    if not isinstance(criteria, dict) or not criteria:
        errors.append("criteria must be a non-empty object")
    elif any(not _number(value) or not 0 <= value <= 10 for value in criteria.values()):
        errors.append("criteria values must be finite numbers from 0 to 10")

    hard_failures = review.get("hard_failures")
    if not isinstance(hard_failures, list) or any(not isinstance(item, str) for item in hard_failures):
        errors.append("hard_failures must be a list of strings")

    feedback = review.get("feedback")
    if not isinstance(feedback, list):
        errors.append("feedback must be a list")
    else:
        for item in feedback:
            if not isinstance(item, dict) or set(item) != {"criterion", "message"}:
                errors.append("feedback entries must contain criterion and message")
                continue
            if not isinstance(item["criterion"], str) or not item["criterion"]:
                errors.append("feedback criterion must be a non-empty string")
            if not isinstance(item["message"], str) or not item["message"].strip():
                errors.append("feedback message must be a non-empty string")
            if isinstance(criteria, dict) and item["criterion"] not in criteria:
                errors.append("feedback criterion must match a criterion")

    artifact = review.get("artifact")
    if not isinstance(artifact, str) or not artifact.strip():
        errors.append("artifact must be a non-empty string")

    if not errors:
        quality_feedback.extend(name for name, score in criteria.items() if score < 9)

    return {
        "valid": not errors,
        "terminal": bool(errors),
        "errors": errors,
        "quality_feedback": quality_feedback,
    }


def _blocked(cycle, reasons, artifact=""):
    return {
        "status": "blocked",
        "cycle_count": cycle,
        "failure_reasons": reasons,
        "last_artifact": artifact,
    }


def run_gauntlet(executor, reviewer, max_cycles=5):
    """Run isolated executor/reviewer cycles and return approved or blocked."""
    if isinstance(max_cycles, bool) or not isinstance(max_cycles, int) or not 1 <= max_cycles <= 5:
        raise ValueError("max_cycles must be an integer between 1 and 5")
    if not callable(executor) or not callable(reviewer):
        return _blocked(0, ["executor/reviewer unavailable"])

    feedback = []
    last_artifact = ""
    for cycle in range(1, max_cycles + 1):
        try:
            last_artifact = executor(feedback)
        except Exception as error:
            return _blocked(cycle, [f"executor unavailable: {error}"], last_artifact)
        if not isinstance(last_artifact, str) or not last_artifact.strip():
            return _blocked(cycle, ["artifact missing"], last_artifact if isinstance(last_artifact, str) else "")

        try:
            result = reviewer(last_artifact, feedback)
        except Exception as error:
            return _blocked(cycle, [f"reviewer unavailable: {error}"], last_artifact)

        validation = validate_review(result)
        if not validation["valid"]:
            return _blocked(cycle, validation["errors"], last_artifact)
        if result["hard_failures"]:
            return _blocked(cycle, result["hard_failures"], last_artifact)

        failed_criteria = set(validation["quality_feedback"])
        provided_criteria = {item["criterion"] for item in result["feedback"]}
        quality_failed = bool(failed_criteria) or result["coverage"] <= 0.99
        if quality_failed:
            if result["coverage"] <= 0.99 and not result["feedback"]:
                return _blocked(cycle, ["feedback missing for coverage gate"], last_artifact)
            if not failed_criteria <= provided_criteria:
                return _blocked(cycle, ["feedback missing for failed criterion"], last_artifact)
            if cycle == max_cycles:
                return _blocked(cycle, ["quality gates not met"], last_artifact)
            feedback = result["feedback"]
            continue

        if result["decision"] == "feedback":
            if not result["feedback"]:
                return _blocked(cycle, ["feedback decision has no actionable feedback"], last_artifact)
            if cycle == max_cycles:
                return _blocked(cycle, ["feedback remained unresolved"], last_artifact)
            feedback = result["feedback"]
            continue

        return {"status": "approved", "cycle_count": cycle, "last_artifact": last_artifact}

    return _blocked(max_cycles, ["maximum cycles exhausted"], last_artifact)
