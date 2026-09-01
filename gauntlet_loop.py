"""Small, deterministic execution contract for the editorial Gauntlet."""

import json
import math
from numbers import Real
import os
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import tempfile


REQUIRED_FIELDS = {"decision", "coverage", "criteria", "hard_failures", "feedback", "artifact"}
DECISIONS = {"approved", "feedback"}
NORMATIVE_CRITERIA = (
    "clareza",
    "força da abertura",
    "originalidade",
    "credibilidade",
    "uso de evidências",
    "risco de alucinação",
    "tom humano",
    "densidade",
    "relevância",
    "consistência com a voz do autor",
    "estrutura obrigatória",
    "pergunta final",
    "tamanho editorial",
    "rastreabilidade das fontes",
)
NORMATIVE_CRITERIA_SET = set(NORMATIVE_CRITERIA)


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
    elif set(criteria) != NORMATIVE_CRITERIA_SET:
        errors.append("criteria must match the normative allowlist exactly")
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


def _blocked(
    cycle, reasons, artifact="", last_review=None, feedback=None, failed_criteria=None,
    *, workspace_root=None,
):
    cycle = cycle if isinstance(cycle, int) and not isinstance(cycle, bool) and 1 <= cycle <= 5 else 1
    artifact = artifact if _relative_artifact(artifact) else ""
    root = Path.cwd().resolve() if workspace_root is None else Path(workspace_root).resolve()
    if not isinstance(last_review, dict) or not validate_review(last_review)["valid"] or last_review.get("artifact") != artifact:
        last_review = {
            "decision": "feedback",
            "coverage": 1.0,
            "criteria": {name: 10 for name in NORMATIVE_CRITERIA},
            "hard_failures": [str(reason) for reason in reasons],
            "feedback": [],
            "artifact": artifact,
        }
        feedback = []
        failed_criteria = []
    if not isinstance(feedback, list):
        feedback = []
    if not isinstance(failed_criteria, list) or any(not isinstance(item, str) for item in failed_criteria):
        failed_criteria = []
    fingerprint = None
    if artifact:
        artifact_file = root / artifact
        try:
            if artifact_file.is_file():
                fingerprint = "sha256:" + sha256(artifact_file.read_bytes()).hexdigest()
        except (UnicodeDecodeError, OSError):
            fingerprint = None
    return {
        "status": "blocked",
        "cycle_count": cycle,
        "cycles": cycle,
        "failure_reasons": [str(reason) for reason in reasons],
        "failed_criteria": sorted(set(failed_criteria)),
        "last_artifact": artifact,
        "last_review": last_review,
        "feedback": feedback,
        "artifact_fingerprint": fingerprint,
    }


def _relative_artifact(value):
    if not isinstance(value, str) or not value.strip():
        return False
    if "\\" in value or (len(value) > 1 and value[1] == ":"):
        return False
    path = Path(value)
    return not path.is_absolute() and value not in {".", ".."} and ".." not in path.parts


def _artifact_path_error(value):
    if isinstance(value, str) and (
        value.startswith(("/", "~")) or (len(value) > 1 and value[1] == ":") or ".." in Path(value).parts
    ):
        return "artifact path is outside root"
    if isinstance(value, str) and "\\" in value:
        return "artifact path must use POSIX separators"
    return "artifact path must be relative"


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
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name} is corrupt") from exc


def _load_events(path):
    events = _load_json(path, [])
    if not isinstance(events, list) or any(not isinstance(event, dict) for event in events):
        raise ValueError("events are invalid")
    return events


def _persist_event(directory, run_id, artifact, cycle, event_type, payload):
    path = directory / "events.yaml"
    events = _load_events(path)
    key = [run_id, artifact, cycle, event_type]
    if not any(event.get("idempotency_key") == key for event in events):
        events.append({"type": event_type, "idempotency_key": key, **payload})
        _atomic_json(path, events)


def _persist_terminal(directory, result):
    _atomic_json(directory / "state.yaml", result)


def _validate_terminal_state(state, artifact_path, root):
    required = {
        "status", "cycles", "cycle_count", "last_artifact", "last_review",
        "feedback", "failed_criteria", "failure_reasons", "artifact_fingerprint",
    }
    if not isinstance(state, dict) or not required <= set(state):
        raise ValueError("state payload is invalid")
    if state["status"] not in {"approved", "blocked"}:
        raise ValueError("state status is invalid")
    failure_reasons = state["failure_reasons"]
    if (
        not isinstance(failure_reasons, list)
        or not failure_reasons
        or any(not isinstance(reason, str) or not reason.strip() for reason in failure_reasons)
    ):
        raise ValueError("state failure reasons are invalid")
    cycles = state["cycles"]
    cycle_count = state["cycle_count"]
    if (
        isinstance(cycles, bool)
        or not isinstance(cycles, int)
        or not 1 <= cycles <= 5
        or isinstance(cycle_count, bool)
        or not isinstance(cycle_count, int)
        or not 1 <= cycle_count <= 5
        or cycles != cycle_count
    ):
        raise ValueError("state cycle count is invalid")
    if not _relative_artifact(state["last_artifact"]) or state["last_artifact"] != artifact_path:
        raise ValueError("state artifact is divergent")
    last_review = state["last_review"]
    if (
        not isinstance(last_review, dict)
        or last_review.get("artifact") != artifact_path
        or not validate_review(last_review)["valid"]
    ):
        raise ValueError("state review is divergent")
    feedback = state["feedback"]
    if (
        not isinstance(feedback, list)
        or any(
            not isinstance(item, dict)
            or set(item) != {"criterion", "message"}
            or not isinstance(item["criterion"], str)
            or not item["criterion"]
            or item["criterion"] not in last_review["criteria"]
            or not isinstance(item["message"], str)
            or not item["message"].strip()
            for item in feedback
        )
        or feedback != last_review["feedback"]
    ):
        raise ValueError("state feedback is invalid")
    failed_criteria = state["failed_criteria"]
    expected_failed = sorted(name for name, score in last_review["criteria"].items() if score < 9)
    if (
        not isinstance(failed_criteria, list)
        or any(not isinstance(item, str) for item in failed_criteria)
        or sorted(failed_criteria) != expected_failed
    ):
        raise ValueError("state failed criteria are invalid")
    if state["status"] == "approved" and (
        last_review["decision"] != "approved"
        or last_review["coverage"] < 0.99
        or expected_failed
        or last_review["hard_failures"]
        or feedback
    ):
        raise ValueError("approved state does not pass acceptance gates")
    try:
        checks = _artifact_checks(root, artifact_path, artifact_path)
        artifact_file = root / artifact_path
        expected = None
        if artifact_file.exists() and artifact_file.is_file():
            expected = "sha256:" + sha256(artifact_file.read_bytes()).hexdigest()
    except (UnicodeDecodeError, OSError) as error:
        raise ValueError(f"artifact validation failed: {error}") from error
    fingerprint = state["artifact_fingerprint"]
    if (
        not isinstance(fingerprint, (str, type(None)))
        or fingerprint is not None and (
            len(fingerprint) != 71
            or not fingerprint.startswith("sha256:")
            or any(character not in "0123456789abcdef" for character in fingerprint[7:])
        )
        or (expected is not None and fingerprint != expected)
        or (expected is None and fingerprint is not None)
        or state["status"] == "approved" and checks
    ):
        raise ValueError("state fingerprint is divergent")


def _terminal(directory, result, workspace_root=None):
    if directory is not None:
        try:
            _persist_terminal(directory, result)
        except (UnicodeDecodeError, OSError) as error:
            return _blocked(
                result.get("cycles", 1),
                [f"persistence error: {error}"],
                result.get("last_artifact", ""),
                result.get("last_review"),
                result.get("feedback", []),
                result.get("failed_criteria", []),
                workspace_root=workspace_root,
            )
    return result


def _artifact_checks(root, expected, actual):
    if not _relative_artifact(expected):
        return [_artifact_path_error(expected)]
    if not _relative_artifact(actual):
        return [_artifact_path_error(actual)]
    if actual != expected:
        return ["artifact differs from expected path"]
    expected_file = (root / expected).resolve()
    if root not in expected_file.parents:
        return ["artifact path is outside root"]
    if not expected_file.exists():
        return ["artifact missing"]
    if not expected_file.is_file():
        return ["artifact not regular"]
    if expected_file.stat().st_size == 0:
        return ["artifact empty"]
    return []


def _partial_review(directory, run_id, artifact, cycle):
    if directory is None:
        return None, []
    path = directory / f"cycle-{cycle:02d}.yaml"
    if not path.exists():
        return None, []
    payload = _load_json(path, None)
    key = [run_id, artifact, cycle]
    if not isinstance(payload, dict) or payload.get("idempotency_key") != key:
        return None, ["partial cycle idempotency key divergent"]
    review = payload.get("review")
    validation = validate_review(review)
    if not validation["valid"] or review.get("artifact") != artifact:
        return None, ["partial cycle payload divergent"]
    return review, []


def run_gauntlet(executor, reviewer, max_cycles=5, *, artifact_path, persistence_dir=None, run_id="run", workspace_root=None):
    """Run isolated executor/reviewer cycles and return approved or blocked."""
    if isinstance(max_cycles, bool) or not isinstance(max_cycles, int) or not 1 <= max_cycles <= 5:
        raise ValueError("max_cycles must be an integer between 1 and 5")
    if not _relative_artifact(artifact_path):
        return _blocked(0, [_artifact_path_error(artifact_path)])
    if not callable(executor) or not callable(reviewer):
        return _blocked(0, ["executor/reviewer unavailable"])
    if executor is reviewer:
        return _blocked(0, ["executor and reviewer must be distinct callbacks"])
    root = Path.cwd().resolve() if workspace_root is None else Path(workspace_root).resolve()
    blocked = lambda *args: _blocked(*args, workspace_root=root)
    directory = Path(persistence_dir) if persistence_dir is not None else None
    if directory is not None:
        if directory.exists() and not directory.is_dir():
            return blocked(0, ["persistence directory is not a directory"])
        state_path = directory / "state.yaml"
        try:
            existing = _load_json(state_path, None)
        except (UnicodeDecodeError, OSError) as error:
            return blocked(0, [f"persistence error: {error}"])
        if state_path.exists():
            if not isinstance(existing, dict):
                return blocked(0, ["state payload is invalid"])
            if existing.get("status") in {"approved", "blocked"}:
                try:
                    _validate_terminal_state(existing, artifact_path, root)
                except ValueError as error:
                    return blocked(0, [str(error)])
                return existing
            return blocked(0, ["state payload is invalid"])
    feedback = []
    last_artifact = ""
    last_review = None
    for cycle in range(1, max_cycles + 1):
        if directory is not None:
            try:
                _persist_event(directory, run_id, artifact_path, cycle, "cycle-start", {"cycle": cycle})
            except (UnicodeDecodeError, OSError) as error:
                return blocked(cycle, [f"persistence error: {error}"], artifact_path)
        try:
            stored_review, partial_errors = _partial_review(directory, run_id, artifact_path, cycle)
        except (UnicodeDecodeError, OSError) as error:
            return blocked(cycle, [f"persistence error: {error}"], artifact_path)
        if partial_errors:
            return _terminal(directory, blocked(cycle, partial_errors, artifact_path), root)
        if stored_review is not None:
            last_artifact = artifact_path
            result = stored_review
            checks = _artifact_checks(root, artifact_path, artifact_path)
        else:
            try:
                last_artifact = executor(deepcopy(feedback))
            except Exception as error:
                return _terminal(directory, blocked(cycle, [f"executor unavailable: {error}"], last_artifact), root)
            checks = _artifact_checks(root, artifact_path, last_artifact)
        if directory is not None:
            try:
                _persist_event(directory, run_id, artifact_path, cycle, "deterministic-checks", {"checks": checks})
            except (UnicodeDecodeError, OSError) as error:
                return blocked(cycle, [f"persistence error: {error}"], last_artifact)
        if checks:
            return _terminal(directory, blocked(cycle, checks, last_artifact), root)

        if stored_review is None:
            try:
                result = reviewer(last_artifact, deepcopy(feedback))
            except Exception as error:
                return _terminal(directory, blocked(cycle, [f"reviewer unavailable: {error}"], last_artifact), root)

            validation = validate_review(result)
            if not validation["valid"]:
                return _terminal(directory, blocked(cycle, validation["errors"], last_artifact, result), root)
        else:
            validation = validate_review(result)
        if result["artifact"] != artifact_path:
            return _terminal(directory, blocked(cycle, ["review artifact differs from expected path"], last_artifact, result), root)
        last_review = result
        if directory is not None:
            try:
                _atomic_json(directory / f"cycle-{cycle:02d}.yaml", {"idempotency_key": [run_id, artifact_path, cycle], "review": result})
                _persist_event(directory, run_id, artifact_path, cycle, "review", {"review": result})
            except (UnicodeDecodeError, OSError) as error:
                return blocked(cycle, [f"persistence error: {error}"], last_artifact, last_review, result["feedback"])
        if result["hard_failures"]:
            return _terminal(directory, blocked(cycle, result["hard_failures"], last_artifact, last_review, result["feedback"]), root)

        failed_criteria = set(validation["quality_feedback"])
        provided_criteria = {item["criterion"] for item in result["feedback"]}
        quality_failed = bool(failed_criteria) or result["coverage"] < 0.99
        if quality_failed:
            if result["coverage"] < 0.99 and not result["feedback"]:
                return _terminal(directory, blocked(cycle, ["feedback missing for coverage gate"], last_artifact, last_review, result["feedback"], sorted(failed_criteria)), root)
            if not failed_criteria <= provided_criteria:
                return _terminal(directory, blocked(cycle, ["feedback missing for failed criterion"], last_artifact, last_review, result["feedback"], sorted(failed_criteria)), root)
            if cycle == max_cycles:
                return _terminal(directory, blocked(cycle, ["quality gates not met"], last_artifact, last_review, result["feedback"], sorted(failed_criteria)), root)
            feedback = deepcopy(result["feedback"])
            continue

        if result["decision"] == "feedback":
            if not result["feedback"]:
                return _terminal(directory, blocked(cycle, ["feedback decision has no actionable feedback"], last_artifact, last_review, result["feedback"]), root)
            if cycle == max_cycles:
                return _terminal(directory, blocked(cycle, ["feedback remained unresolved"], last_artifact, last_review, result["feedback"]), root)
            feedback = deepcopy(result["feedback"])
            continue

        return _terminal(directory, {
            "status": "approved", "cycle_count": cycle, "cycles": cycle,
            "last_artifact": last_artifact, "last_review": last_review,
            "feedback": [], "failed_criteria": [], "failure_reasons": ["approved"],
            "artifact_fingerprint": "sha256:" + sha256((root / last_artifact).read_bytes()).hexdigest(),
        }, root)

    return _terminal(directory, blocked(max_cycles, ["maximum cycles exhausted"], last_artifact, last_review, feedback), root)
