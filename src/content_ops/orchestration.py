"""Fail-closed orchestration protocol for executor/reviewer block cycles."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path

from content_ops.db import Database


BLOCK_ORDER = ("B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B10", "B9", "B11")


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
    checks: list[dict[str, object]] = []
    for check in value["checks"]:
        if not isinstance(check, dict) or not {"name", "status", "evidence"} <= set(check):
            raise InvalidReviewResult("Every check requires name, status, and evidence")
        if not all(isinstance(check[key], str) and check[key] for key in ("name", "status", "evidence")):
            raise InvalidReviewResult("Check name, status, and evidence must be non-empty strings")
        checks.append(check)
    return ReviewResult(value["decision"], value["artifact"], value["feedback"], checks)


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
    if not artifact_path or Path(artifact_path).is_absolute():
        raise WorkflowBlocked("Artifact path must be relative to the repository")
    root = database.path.parent.parent.resolve()
    path = (root / artifact_path).resolve()
    if not path.is_relative_to(root) or (require_exists and not path.is_file()):
        raise WorkflowBlocked("Artifact does not exist within the repository")
    return path


def _validate_completion_request(database: Database, block: str, artifact_path: str) -> None:
    if block == "B7":
        raise WorkflowBlocked("B7 requires mandatory human completion")
    _artifact_path(database, artifact_path)


def can_complete_block(database: Database, round_id: int, block: str, artifact_path: str, cycle: int) -> None:
    """Check every durable and filesystem gate before a block completion event."""
    _validate_completion_request(database, block, artifact_path)
    with database.transaction() as connection:
        _validate_completion(connection, round_id, block, artifact_path, cycle)


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
    if block not in BLOCK_ORDER:
        raise WorkflowBlocked(f"Unknown workflow block: {block}")
    _artifact_path(database, artifact_path, require_exists=block not in {"B1", "B2", "B3"})
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
        connection.execute(
            "INSERT INTO block_cycles (round_id, block, cycle, artifact_path) VALUES (?, ?, ?, ?)",
            (round_id, block, cycle, artifact_path),
        )
        connection.execute(
            "INSERT INTO workflow_events (round_id, block, event, payload_json) VALUES (?, ?, 'cycle_started', ?)",
            (round_id, block, json.dumps({"cycle": cycle, "artifact": artifact_path})),
        )
    return cycle


def record_review(database: Database, round_id: int, block: str, artifact_path: str, cycle: int, reviewer: str, raw: str) -> ReviewResult:
    """Validate and persist one review receipt without private DB access at the CLI."""
    result = parse_review_result(raw)
    if result.artifact != artifact_path:
        raise WorkflowBlocked("Review artifact does not match the requested artifact")
    _artifact_path(database, artifact_path)
    if block == "B7" and result.decision == "approved":
        raise WorkflowBlocked("B7 cannot be approved automatically")
    result_hash = hashlib.sha256(
        json.dumps(json.loads(raw), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
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
        completed = {row["block"] for row in connection.execute(
            "SELECT block FROM workflow_events WHERE round_id = ? "
            "AND event IN ('block_completed', 'human_completed')", (round_id,)
        )}
        validate_block_order(completed, block)
        for row in connection.execute(
            "SELECT result_json FROM review_receipts JOIN block_cycles ON block_cycles.id = review_receipts.cycle_id "
            "WHERE block_cycles.round_id = ? AND block_cycles.block = ? AND block_cycles.artifact_path = ?",
            (round_id, block, artifact_path),
        ):
            prior_hash = hashlib.sha256(
                json.dumps(json.loads(row["result_json"]), sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            if prior_hash == result_hash:
                raise WorkflowBlocked("Repeated review result indicates an unproductive loop")
        connection.execute(
            "INSERT INTO review_receipts (cycle_id, reviewer_agent, decision, result_json) VALUES (?, ?, ?, ?)",
            (cycle_row["id"], reviewer, result.decision, raw),
        )
    return result


def record_human_completion(database: Database, round_id: int, block: str, artifact_path: str, selection: str) -> int:
    """Persist the mandatory human B7 selection without a reviewer receipt."""
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
            "SELECT cycle FROM block_cycles "
            "WHERE round_id = ? AND block = ? AND artifact_path = ? "
            "ORDER BY cycle DESC LIMIT 1",
            (round_id, block, artifact_path),
        ).fetchone()
        if cycle_row is None:
            raise WorkflowBlocked("No matching B7 block cycle")
        event = connection.execute(
            "INSERT INTO workflow_events (round_id, block, event, payload_json) VALUES (?, ?, 'human_completed', ?)",
            (round_id, block, json.dumps({
                "artifact": artifact_path,
                "cycle": cycle_row["cycle"],
                "selection": selection,
            })),
        )
        return event.lastrowid


def complete_block(database: Database, round_id: int, block: str, artifact_path: str, cycle: int) -> int:
    """Check gates and record exactly one completion event in one transaction."""
    _validate_completion_request(database, block, artifact_path)
    with database.transaction() as connection:
        return _complete_block_in_transaction(
            connection, round_id, block, artifact_path, cycle
        )


def complete_block_with_compatibility(
    database: Database, round_id: int, block: str, artifact_path: str, cycle: int
) -> int:
    """Complete a block and write the legacy validation row atomically."""
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


def _complete_block_in_transaction(
    connection, round_id: int, block: str, artifact_path: str, cycle: int
) -> int:
    _validate_completion(connection, round_id, block, artifact_path, cycle)
    event = connection.execute(
        "INSERT INTO workflow_events (round_id, block, event, payload_json) VALUES (?, ?, 'block_completed', ?)",
        (round_id, block, json.dumps({"cycle": cycle, "artifact": artifact_path})),
    )
    return event.lastrowid
