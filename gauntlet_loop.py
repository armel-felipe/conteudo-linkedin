"""Small, deterministic execution contract for the editorial Gauntlet."""

import json
import math
from numbers import Real
import os
from copy import deepcopy
from pathlib import Path
import tempfile


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


def _blocked(cycle, reasons, artifact="", last_review=None, feedback=None, failed_criteria=None):
    return {
        "status": "blocked",
        "cycle_count": cycle,
        "cycles": cycle,
        "failure_reasons": reasons,
        "failed_criteria": [] if failed_criteria is None else failed_criteria,
        "last_artifact": artifact,
        "last_review": last_review,
        "feedback": [] if feedback is None else feedback,
    }


def _relative_artifact(value):
    if not isinstance(value, str) or not value.strip():
        return False
    path = Path(value)
    return not path.is_absolute() and value not in {".", ".."} and ".." not in path.parts


def _atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=f".{path.name}.", delete=False) as stream:
        temp_path = Path(stream.name)
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
    os.replace(temp_path, path)


def _load_json(path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _persist_event(directory, run_id, artifact, cycle, event_type, payload):
    path = directory / "events.yaml"
    events = _load_json(path, [])
    key = [run_id, artifact, cycle, event_type]
    if not any(event.get("idempotency_key") == key for event in events):
        events.append({"type": event_type, "idempotency_key": key, **payload})
        _atomic_json(path, events)


def _persist_terminal(directory, result):
    _atomic_json(directory / "state.yaml", result)


def _terminal(directory, result):
    if directory is not None:
        _persist_terminal(directory, result)
    return result


def run_gauntlet(executor, reviewer, max_cycles=5, *, artifact_path, persistence_dir=None, run_id="run"):
    """Run isolated executor/reviewer cycles and return approved or blocked."""
    if isinstance(max_cycles, bool) or not isinstance(max_cycles, int) or not 1 <= max_cycles <= 5:
        raise ValueError("max_cycles must be an integer between 1 and 5")
    if not _relative_artifact(artifact_path):
        return _blocked(0, ["artifact path must be relative"])
    directory = Path(persistence_dir) if persistence_dir is not None else None
    if directory is not None:
        existing = _load_json(directory / "state.yaml", None)
        if isinstance(existing, dict) and existing.get("status") in {"approved", "blocked"}:
            return existing
    if not callable(executor) or not callable(reviewer):
        return _terminal(directory, _blocked(0, ["executor/reviewer unavailable"]))

    feedback = []
    last_artifact = ""
    last_review = None
    for cycle in range(1, max_cycles + 1):
        if directory is not None:
            _persist_event(directory, run_id, artifact_path, cycle, "cycle-start", {"cycle": cycle})
        try:
            last_artifact = executor(deepcopy(feedback))
        except Exception as error:
            return _terminal(directory, _blocked(cycle, [f"executor unavailable: {error}"], last_artifact))
        checks = []
        if not _relative_artifact(last_artifact):
            checks.append("artifact must be relative")
        elif last_artifact != artifact_path:
            checks.append("artifact differs from expected path")
        if directory is not None:
            _persist_event(directory, run_id, artifact_path, cycle, "deterministic-checks", {"checks": checks})
        if checks:
            return _terminal(directory, _blocked(cycle, checks, last_artifact))

        try:
            result = reviewer(last_artifact, deepcopy(feedback))
        except Exception as error:
            return _terminal(directory, _blocked(cycle, [f"reviewer unavailable: {error}"], last_artifact))

        validation = validate_review(result)
        if not validation["valid"]:
            return _terminal(directory, _blocked(cycle, validation["errors"], last_artifact, result))
        if result["artifact"] != artifact_path:
            return _terminal(directory, _blocked(cycle, ["review artifact differs from expected path"], last_artifact, result))
        last_review = result
        if directory is not None:
            _atomic_json(directory / f"cycle-{cycle:02d}.yaml", {"idempotency_key": [run_id, artifact_path, cycle], "review": result})
            _persist_event(directory, run_id, artifact_path, cycle, "review", {"review": result})
        if result["hard_failures"]:
            return _terminal(directory, _blocked(cycle, result["hard_failures"], last_artifact, last_review, result["feedback"]))

        failed_criteria = set(validation["quality_feedback"])
        provided_criteria = {item["criterion"] for item in result["feedback"]}
        quality_failed = bool(failed_criteria) or result["coverage"] <= 0.99
        if quality_failed:
            if result["coverage"] <= 0.99 and not result["feedback"]:
                return _terminal(directory, _blocked(cycle, ["feedback missing for coverage gate"], last_artifact, last_review, result["feedback"], sorted(failed_criteria)))
            if not failed_criteria <= provided_criteria:
                return _terminal(directory, _blocked(cycle, ["feedback missing for failed criterion"], last_artifact, last_review, result["feedback"], sorted(failed_criteria)))
            if cycle == max_cycles:
                return _terminal(directory, _blocked(cycle, ["quality gates not met"], last_artifact, last_review, result["feedback"], sorted(failed_criteria)))
            feedback = deepcopy(result["feedback"])
            continue

        if result["decision"] == "feedback":
            if not result["feedback"]:
                return _terminal(directory, _blocked(cycle, ["feedback decision has no actionable feedback"], last_artifact, last_review, result["feedback"]))
            if cycle == max_cycles:
                return _terminal(directory, _blocked(cycle, ["feedback remained unresolved"], last_artifact, last_review, result["feedback"]))
            feedback = deepcopy(result["feedback"])
            continue

        return _terminal(directory, {"status": "approved", "cycle_count": cycle, "cycles": cycle, "last_artifact": last_artifact, "last_review": last_review, "feedback": []})

    return _terminal(directory, _blocked(max_cycles, ["maximum cycles exhausted"], last_artifact, last_review, feedback))
