"""Fail-closed orchestration protocol for executor/reviewer block cycles."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re

from content_ops.db import Database


BLOCK_ORDER = ("B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B10", "B9", "B11")
_SECRET_KEY = re.compile(r"(?:^|_)(?:API[_-]?KEY|TOKEN|PASSWORD)$|^CT0$", re.IGNORECASE)
_SECRET_VALUE = re.compile(
    r"(?P<name>(?:[A-Za-z0-9_]*(?:API[_-]?KEY|TOKEN|PASSWORD)|AUTH_TOKEN|CT0))\s*=\s*[^\s,;&]+",
    re.IGNORECASE,
)
_REDACTED = "[REDACTED]"


class InvalidReviewResult(ValueError):
    """Raised when a reviewer result does not match the required schema."""


class WorkflowBlocked(ValueError):
    """Raised when a workflow gate cannot be passed safely."""


@dataclass(frozen=True)
class ReviewResult:
    decision: str
    artifact: str
    feedback: list[object]
    checks: list[dict[str, object]]


def redact_event_payload(payload: dict) -> dict:
    """Return a defensive, recursively redacted copy suitable for event storage."""
    def redact(value: object) -> object:
        if isinstance(value, dict):
            return {
                key: _REDACTED if isinstance(key, str) and _SECRET_KEY.search(key)
                else redact(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [redact(item) for item in value]
        if isinstance(value, tuple):
            return [redact(item) for item in value]
        if isinstance(value, str):
            return _SECRET_VALUE.sub(
                lambda match: f"{match.group('name')}=[REDACTED]", value
            )
        return value

    return redact(payload)


def parse_review_result(raw: str) -> ReviewResult:
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        raise InvalidReviewResult("Review result must be valid JSON") from None
    if not isinstance(value, dict) or set(value) != {"decision", "artifact", "feedback", "checks"}:
        raise InvalidReviewResult("Review result must contain exactly decision, artifact, feedback, and checks")
    if value["decision"] not in {"approved", "feedback"}:
        raise InvalidReviewResult("Review decision must be 'approved' or 'feedback'")
    if not isinstance(value["artifact"], str) or not value["artifact"] or Path(value["artifact"]).is_absolute():
        raise InvalidReviewResult("Review artifact must be a relative path")
    if not isinstance(value["feedback"], list) or not isinstance(value["checks"], list) or not value["checks"]:
        raise InvalidReviewResult("Review feedback and checks must be lists, with at least one check")
    if value["decision"] == "approved" and value["feedback"]:
        raise InvalidReviewResult("Approved review results must have empty feedback")
    if value["decision"] == "feedback" and not value["feedback"]:
        raise InvalidReviewResult("Feedback review results require at least one feedback item")
    if value["decision"] == "feedback":
        for item in value["feedback"]:
            if not isinstance(item, dict) or not all(
                isinstance(item.get(field), str) and item[field].strip()
                for field in ("contract", "problem", "required_change")
            ):
                raise InvalidReviewResult(
                    "Every feedback item requires non-empty contract, problem, and required_change"
                )
    checks: list[dict[str, object]] = []
    for check in value["checks"]:
        if not isinstance(check, dict) or not {"name", "status", "evidence"} <= set(check):
            raise InvalidReviewResult("Every check requires name, status, and evidence")
        if not all(isinstance(check[key], str) and check[key] for key in ("name", "status", "evidence")):
            raise InvalidReviewResult("Check name, status, and evidence must be non-empty strings")
        checks.append(check)
    return ReviewResult(value["decision"], value["artifact"], value["feedback"], checks)


def _feedback_hash(result: ReviewResult) -> str:
    return hashlib.sha256(
        json.dumps(
            redact_event_payload({"feedback": result.feedback})["feedback"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _event(connection, round_id: int, block: str, event: str, payload: dict) -> int:
    return connection.execute(
        "INSERT INTO workflow_events (round_id, block, event, payload_json) VALUES (?, ?, ?, ?)",
        (round_id, block, event, json.dumps(redact_event_payload(payload), ensure_ascii=False, sort_keys=True)),
    ).lastrowid


def resume_round(database: Database, round_id: int) -> str:
    """Return the next safe action from events; persist only terminal blocks."""
    with database.transaction() as connection:
        round_row = connection.execute("SELECT status FROM rounds WHERE id = ?", (round_id,)).fetchone()
        if round_row is None:
            return "blocked"
        if round_row["status"] != "open":
            if round_row["status"] != "closed":
                return "blocked"
            complete = True
            for block in BLOCK_ORDER:
                state = connection.execute(
                    "SELECT event FROM workflow_events WHERE round_id = ? AND block = ? "
                    "ORDER BY id DESC LIMIT 1", (round_id, block)
                ).fetchone()
                if state is None or state["event"] not in {"block_completed", "human_completed"}:
                    complete = False
                    break
            return "complete" if complete else "blocked"
        for block in BLOCK_ORDER:
            state = connection.execute(
                "SELECT event, payload_json FROM workflow_events WHERE round_id = ? AND block = ? "
                "ORDER BY id DESC LIMIT 1", (round_id, block)
            ).fetchone()
            if state is None:
                return f"start:{block}"
            if state["event"] in {"failed", "blocked"}:
                return "blocked"
            if state["event"] in {"block_completed", "human_completed"}:
                continue
            payload = json.loads(state["payload_json"])
            if block == "B7":
                return "human:B7"
            if state["event"] == "cycle_started":
                if payload.get("review_decision") == "approved":
                    return f"complete:{block}"
                if payload.get("review_decision") == "feedback":
                    cycle = int(payload["cycle"])
                    if cycle >= _max_review_cycles():
                        _event(connection, round_id, block, "blocked", {
                            "cycle": cycle, "reason": "review cycle limit reached"
                        })
                        return "blocked"
                    return f"start:{block}:{cycle + 1}"
                return f"review:{block}"
            if state["event"] == "review_approved":
                return f"complete:{block}"
            if state["event"] == "review_feedback":
                cycle = int(payload["cycle"])
                if cycle >= _max_review_cycles():
                    _event(connection, round_id, block, "blocked", {
                        "cycle": cycle, "reason": "review cycle limit reached"
                    })
                    return "blocked"
                return f"start:{block}:{cycle + 1}"
            _event(connection, round_id, block, "blocked", {"reason": "unknown workflow event"})
            return "blocked"
        return "complete"


def validate_block_order(completed: set[str], requested: str) -> None:
    if requested not in BLOCK_ORDER:
        raise WorkflowBlocked(f"Unknown workflow block: {requested}")
    if requested in completed:
        raise WorkflowBlocked(f"Block {requested} is already complete")
    index = BLOCK_ORDER.index(requested)
    missing = [block for block in BLOCK_ORDER[:index] if block not in completed]
    if missing:
        raise WorkflowBlocked(f"Block {requested} is out of order; missing {', '.join(missing)}")


def _artifact_path(database: Database, artifact_path: str, *, require_exists: bool = True) -> Path:
    try:
        if not artifact_path or Path(artifact_path).is_absolute():
            raise WorkflowBlocked("Artifact path must be relative to the repository")
        root = database.path.parent.parent.resolve()
        path = (root / artifact_path).resolve()
        if not path.is_relative_to(root) or (require_exists and not path.is_file()):
            raise WorkflowBlocked("Artifact does not exist within the repository")
        if require_exists and path.is_file() and _SECRET_VALUE.search(path.read_text(encoding="utf-8")):
            raise WorkflowBlocked("Artifact contains prohibited credential-shaped content")
        return path
    except WorkflowBlocked:
        raise
    except (OSError, UnicodeError):
        # Never persist filesystem error details, which may contain artifact data.
        raise WorkflowBlocked("Artifact could not be read safely") from None


def _validate_reference(database: Database, block: str, reference: str, *, require_exists: bool = True) -> None:
    if block == "B2":
        if not database.pillar_is_approved(reference):
            raise WorkflowBlocked("B2 selection must name an approved pillar")
        return
    _artifact_path(database, reference, require_exists=require_exists)


def _persist_blocked(database: Database, round_id: int, block: str, cycle: int, reason: str) -> None:
    try:
        with database.transaction() as connection:
            round_row = connection.execute(
                "SELECT status FROM rounds WHERE id = ?", (round_id,)
            ).fetchone()
            if round_row is None or block not in BLOCK_ORDER:
                return
            _event(connection, round_id, block, "blocked", {"cycle": cycle, "reason": reason})
    except Exception:
        # Preserve the gate error if the diagnostic write itself cannot commit.
        pass


def _validate_completion_request(database: Database, block: str, artifact_path: str) -> None:
    if block == "B7":
        raise WorkflowBlocked("B7 requires mandatory human completion")
    _validate_reference(database, block, artifact_path)


def can_complete_block(database: Database, round_id: int, block: str, artifact_path: str, cycle: int) -> None:
    """Check every durable and filesystem gate before a block completion event."""
    try:
        _validate_completion_request(database, block, artifact_path)
        with database.transaction() as connection:
            _validate_completion(connection, round_id, block, artifact_path, cycle)
    except WorkflowBlocked as error:
        _persist_blocked(database, round_id, block, cycle, str(error))
        raise


def _validate_completion(connection, round_id: int, block: str, artifact_path: str, cycle: int):
    round_row = connection.execute("SELECT status FROM rounds WHERE id = ?", (round_id,)).fetchone()
    if round_row is None or round_row["status"] != "open":
        raise WorkflowBlocked("Round is not active")
    cycle_row = connection.execute(
        "SELECT id FROM block_cycles WHERE round_id = ? AND block = ? AND cycle = ? AND artifact_path = ?",
        (round_id, block, cycle, artifact_path),
    ).fetchone()
    if cycle_row is None:
        raise WorkflowBlocked("No matching block cycle")
    latest_cycle = connection.execute(
        "SELECT MAX(cycle) AS cycle FROM block_cycles WHERE round_id = ? AND block = ?",
        (round_id, block),
    ).fetchone()["cycle"]
    if cycle != latest_cycle:
        raise WorkflowBlocked("Completion cycle is no longer active")
    completed = {row["block"] for row in connection.execute(
        "SELECT block FROM workflow_events WHERE round_id = ? "
        "AND event IN ('block_completed', 'human_completed')", (round_id,)
    )}
    validate_block_order(completed, block)
    if not connection.execute(
        "SELECT 1 FROM review_receipts WHERE cycle_id = ? AND decision = 'approved' LIMIT 1",
        (cycle_row["id"],),
    ).fetchone():
        raise WorkflowBlocked("An approved review receipt is required")
    return cycle_row


def _max_review_cycles() -> int:
    try:
        maximum = int(os.environ.get("ORCHESTRATOR_MAX_REVIEW_CYCLES", "3"))
    except ValueError:
        raise WorkflowBlocked("ORCHESTRATOR_MAX_REVIEW_CYCLES must be an integer") from None
    if maximum < 1:
        raise WorkflowBlocked("ORCHESTRATOR_MAX_REVIEW_CYCLES must be positive")
    return maximum


def start_block_cycle(database: Database, round_id: int, block: str, artifact_path: str) -> int:
    """Validate and atomically start the next bounded executor cycle."""
    try:
        if block not in BLOCK_ORDER:
            raise WorkflowBlocked(f"Unknown workflow block: {block}")
        _validate_reference(database, block, artifact_path, require_exists=block not in {"B1", "B2", "B3"})
        with database.transaction() as connection:
            round_row = connection.execute("SELECT status FROM rounds WHERE id = ?", (round_id,)).fetchone()
            if round_row is None or round_row["status"] != "open":
                raise WorkflowBlocked("Round is not active")
            row = connection.execute(
                "SELECT COALESCE(MAX(cycle), 0) AS cycle FROM block_cycles WHERE round_id = ? AND block = ?",
                (round_id, block),
            ).fetchone()
            cycle = row["cycle"] + 1
            completed = {item["block"] for item in connection.execute(
                "SELECT block FROM workflow_events WHERE round_id = ? "
                "AND event IN ('block_completed', 'human_completed')", (round_id,)
            )}
            validate_block_order(completed, block)
            if cycle > _max_review_cycles():
                raise WorkflowBlocked(f"Review cycle limit reached for {block}")
            latest = connection.execute(
                "SELECT event, payload_json FROM workflow_events WHERE round_id = ? AND block = ? "
                "ORDER BY id DESC LIMIT 1", (round_id, block)
            ).fetchone()
            if latest is not None:
                latest_payload = json.loads(latest["payload_json"])
                if latest["event"] in {"review_approved", "block_completed", "human_completed"}:
                    raise WorkflowBlocked(f"Block {block} already has an approval or completion")
                if latest["event"] == "cycle_started" and latest_payload.get("review_decision") == "approved":
                    raise WorkflowBlocked(f"Block {block} already has an approval or completion")
            connection.execute(
                "INSERT INTO block_cycles (round_id, block, cycle, artifact_path) VALUES (?, ?, ?, ?)",
                (round_id, block, cycle, artifact_path),
            )
            _event(connection, round_id, block, "cycle_started", {"cycle": cycle, "artifact": artifact_path})
        return cycle
    except WorkflowBlocked as error:
        _persist_blocked(database, round_id, block, 0, str(error))
        raise


def record_review(database: Database, round_id: int, block: str, artifact_path: str, cycle: int, reviewer: str, raw: str) -> ReviewResult:
    """Validate and persist one review receipt without private DB access at the CLI."""
    try:
        result = parse_review_result(raw)
    except InvalidReviewResult:
        try:
            database.record_workflow_failure(
                round_id, block, "invalid reviewer response", {"kind": "invalid-response"}
            )
        except (ValueError, WorkflowBlocked):
            pass
        raise
    if result.artifact != artifact_path:
        with database.transaction() as connection:
            _event(connection, round_id, block, "blocked", {"cycle": cycle, "reason": "review artifact mismatch"})
        raise WorkflowBlocked("Review artifact does not match the requested artifact")
    try:
        _validate_reference(database, block, artifact_path)
    except WorkflowBlocked as error:
        with database.transaction() as connection:
            _event(connection, round_id, block, "blocked", {"cycle": cycle, "reason": str(error)})
        raise
    if block == "B7" and result.decision == "approved":
        _persist_blocked(database, round_id, block, cycle, "B7 cannot be approved automatically")
        raise WorkflowBlocked("B7 cannot be approved automatically")
    if result.decision == "feedback":
        with database.transaction() as connection:
            repeated = False
            for row in connection.execute(
                "SELECT result_json FROM review_receipts JOIN block_cycles ON block_cycles.id = review_receipts.cycle_id "
                "WHERE block_cycles.round_id = ? AND block_cycles.block = ? AND block_cycles.artifact_path = ?",
                (round_id, block, artifact_path),
            ):
                if _feedback_hash(parse_review_result(row["result_json"])) == _feedback_hash(result):
                    repeated = True
                    break
        if repeated:
            _persist_blocked(database, round_id, block, cycle, "Repeated review result indicates an unproductive loop")
            raise WorkflowBlocked("Repeated review result indicates an unproductive loop")
    with database.transaction() as connection:
        round_row = connection.execute("SELECT status FROM rounds WHERE id = ?", (round_id,)).fetchone()
        if round_row is None or round_row["status"] != "open":
            raise WorkflowBlocked("Round is not active")
        cycle_row = connection.execute(
            "SELECT id FROM block_cycles WHERE round_id = ? AND block = ? AND cycle = ? AND artifact_path = ?",
            (round_id, block, cycle, artifact_path),
        ).fetchone()
        if cycle_row is None:
            raise WorkflowBlocked("No matching block cycle")
        latest_cycle = connection.execute(
            "SELECT MAX(cycle) AS cycle FROM block_cycles WHERE round_id = ? AND block = ?",
            (round_id, block),
        ).fetchone()["cycle"]
        if cycle != latest_cycle:
            _event(connection, round_id, block, "blocked", {
                "cycle": cycle, "reason": "review cycle is no longer active"
            })
            raise WorkflowBlocked("Review cycle is no longer active")
        if connection.execute(
            "SELECT 1 FROM review_receipts WHERE cycle_id = ? AND decision = 'approved' LIMIT 1",
            (cycle_row["id"],),
        ).fetchone():
            raise WorkflowBlocked("Cannot record a review after approval")
        completed = {row["block"] for row in connection.execute(
            "SELECT block FROM workflow_events WHERE round_id = ? "
            "AND event IN ('block_completed', 'human_completed')", (round_id,)
        )}
        validate_block_order(completed, block)
        stored_result = json.dumps(
            redact_event_payload(json.loads(raw)), ensure_ascii=False, sort_keys=True
        )
        connection.execute(
            "INSERT INTO review_receipts (cycle_id, reviewer_agent, decision, result_json) VALUES (?, ?, ?, ?)",
            (cycle_row["id"], reviewer, result.decision, stored_result),
        )
        _event(connection, round_id, block, f"review_{result.decision}", {
            "cycle": cycle, "artifact": artifact_path, "feedback": result.feedback,
            "feedback_hash": _feedback_hash(result),
        })
        # Keep the original cycle marker as the compatibility-facing latest state.
        _event(connection, round_id, block, "cycle_started", {
            "cycle": cycle, "artifact": artifact_path, "state": "reviewed",
            "review_decision": result.decision,
        })
    return result


def record_human_completion(database: Database, round_id: int, block: str, artifact_path: str, selection: str) -> int:
    """Persist the mandatory human B7 selection without a reviewer receipt."""
    try:
        if block != "B7":
            raise WorkflowBlocked("Human completion is only available for B7")
        if not selection:
            raise WorkflowBlocked("B7 human selection is required")
        _artifact_path(database, artifact_path)
        with database.transaction() as connection:
            round_row = connection.execute("SELECT status FROM rounds WHERE id = ?", (round_id,)).fetchone()
            if round_row is None or round_row["status"] != "open":
                raise WorkflowBlocked("Round is not active")
            completed = {row["block"] for row in connection.execute(
                "SELECT block FROM workflow_events WHERE round_id = ? AND event IN ('block_completed', 'human_completed')", (round_id,)
            )}
            validate_block_order(completed, block)
            cycle_row = connection.execute(
                "SELECT cycle, artifact_path FROM block_cycles "
                "WHERE round_id = ? AND block = ? ORDER BY cycle DESC LIMIT 1",
                (round_id, block),
            ).fetchone()
            if cycle_row is None:
                raise WorkflowBlocked("No matching B7 block cycle")
            if cycle_row["artifact_path"] != artifact_path:
                raise WorkflowBlocked("B7 artifact does not match the latest block cycle")
            return _event(connection, round_id, block, "human_completed", {
                "artifact": artifact_path,
                "cycle": cycle_row["cycle"],
                "selection": selection,
            })
    except WorkflowBlocked as error:
        _persist_blocked(database, round_id, block, 0, str(error))
        raise


def complete_block(database: Database, round_id: int, block: str, artifact_path: str, cycle: int) -> int:
    """Check gates and record exactly one completion event in one transaction."""
    try:
        _validate_completion_request(database, block, artifact_path)
        with database.transaction() as connection:
            return _complete_block_in_transaction(
                connection, round_id, block, artifact_path, cycle
            )
    except WorkflowBlocked as error:
        _persist_blocked(database, round_id, block, cycle, str(error))
        raise


def complete_block_with_compatibility(
    database: Database, round_id: int, block: str, artifact_path: str, cycle: int
) -> int:
    """Complete a block and write the legacy validation row atomically."""
    try:
        _validate_completion_request(database, block, artifact_path)
        with database.transaction() as connection:
            event_id = _complete_block_in_transaction(
                connection, round_id, block, artifact_path, cycle
            )
            connection.execute(
                "INSERT INTO block_validations (block, artifact_path) VALUES (?, ?)",
                (block, artifact_path),
            )
            return event_id
    except WorkflowBlocked as error:
        _persist_blocked(database, round_id, block, cycle, str(error))
        raise


def _complete_block_in_transaction(
    connection, round_id: int, block: str, artifact_path: str, cycle: int
) -> int:
    _validate_completion(connection, round_id, block, artifact_path, cycle)
    return _event(connection, round_id, block, "block_completed", {"cycle": cycle, "artifact": artifact_path})
