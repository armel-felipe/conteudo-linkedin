"""Fail-closed orchestration protocol for executor/reviewer block cycles."""

from dataclasses import dataclass
import json
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


def _artifact_path(database: Database, artifact_path: str) -> Path:
    if not artifact_path or Path(artifact_path).is_absolute():
        raise WorkflowBlocked("Artifact path must be relative to the repository")
    root = database.path.parent.parent.resolve()
    path = (root / artifact_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise WorkflowBlocked("Artifact does not exist within the repository")
    return path


def can_complete_block(database: Database, round_id: int, block: str, artifact_path: str, cycle: int) -> None:
    """Check every durable and filesystem gate before a block completion event."""
    if block == "B7":
        raise WorkflowBlocked("B7 requires mandatory human completion")
    _artifact_path(database, artifact_path)
    with database._connect() as connection:
        round_row = connection.execute("SELECT status FROM rounds WHERE id = ?", (round_id,)).fetchone()
        if round_row is None or round_row["status"] != "open":
            raise WorkflowBlocked("Round is not active")
        cycle_row = connection.execute(
            "SELECT id FROM block_cycles WHERE round_id = ? AND block = ? AND cycle = ? AND artifact_path = ?",
            (round_id, block, cycle, artifact_path),
        ).fetchone()
        if cycle_row is None:
            raise WorkflowBlocked("No matching block cycle")
        completed = {
            row["block"] for row in connection.execute(
                "SELECT block FROM workflow_events WHERE round_id = ? AND event = 'block_completed'",
                (round_id,),
            )
        }
    validate_block_order(completed, block)
    if not database.review_is_approved(round_id, block, artifact_path, cycle):
        raise WorkflowBlocked("An approved review receipt is required")
