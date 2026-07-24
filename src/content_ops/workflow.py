"""Editorial workflow operations that keep research, ideas, and drafts linked."""

from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from content_ops.db import Database
from content_ops.markdown import read_post_record, write_post_record
from content_ops.models import PostStatus


class SchedulingValidationError(ValueError):
    """Raised when a scheduling gate rejects a post before network activity."""


class SchedulingError(RuntimeError):
    """A sanitized error after a single unsuccessful scheduling attempt."""


def approve_draft(
    post_id: int, markdown_path: str | Path, database: Database | None = None
) -> None:
    """Record human approval in both stores, compensating for write failures."""
    path = Path(markdown_path)
    metadata, body = read_post_record(path)
    if metadata.get("status") != PostStatus.IN_REVIEW.value:
        raise SchedulingValidationError("Post is not in review")
    original = path.read_bytes()
    metadata["approved"] = True
    metadata["status"] = PostStatus.APPROVED.value
    try:
        if database is None:
            write_post_record(path, metadata, body)
            return
        with database.transaction() as connection:
            database.transition_post(post_id, PostStatus.APPROVED, connection)
            write_post_record(path, metadata, body)
    except BaseException:
        if path.exists() and path.read_bytes() != original:
            path.write_bytes(original)
        raise


def schedule_post(
    post_id: int,
    markdown_path: str | Path,
    scheduled_for: str,
    confirmed: bool,
    client: object,
    database: Database | None = None,
) -> str:
    """Schedule an approved record once; validation always completes before HTTP."""
    path = Path(markdown_path)
    try:
        metadata, body = read_post_record(path)
    except ValueError as error:
        raise SchedulingValidationError(str(error)) from None
    _validate_schedule(post_id, metadata, body, scheduled_for, confirmed, database)
    payload: dict[str, object] = {
        "content": body,
        "scheduledFor": scheduled_for,
        "timezone": "America/Sao_Paulo",
        "targets": [{"platform": "linkedin"}],
    }
    image_url = metadata.get("image_url")
    if image_url:
        payload["mediaItems"] = [{"url": image_url}]
    try:
        zernio_post_id = client.create_post(payload)
    except Exception as error:
        _write_schedule_result(path, metadata, body, post_id, PostStatus.FAILED, database)
        raise SchedulingError("Scheduling request failed") from None
    if not isinstance(zernio_post_id, str) or not zernio_post_id:
        _write_schedule_result(path, metadata, body, post_id, PostStatus.FAILED, database)
        raise SchedulingError("Scheduling request failed")
    metadata["zernio_post_id"] = zernio_post_id
    _write_schedule_result(path, metadata, body, post_id, PostStatus.SCHEDULED, database)
    return zernio_post_id


def _validate_schedule(
    post_id: int,
    metadata: dict,
    body: str,
    scheduled_for: str,
    confirmed: bool,
    database: Database | None,
) -> None:
    if not confirmed:
        raise SchedulingValidationError("--confirm is required")
    if metadata.get("status") != PostStatus.APPROVED.value or metadata.get("approved") is not True:
        raise SchedulingValidationError("Both database and Markdown approvals are required")
    if not body.strip():
        raise SchedulingValidationError("Post body cannot be empty")
    image_url = metadata.get("image_url")
    if image_url and (
        not isinstance(image_url, str)
        or urlparse(image_url).scheme not in {"http", "https"}
    ):
        raise SchedulingValidationError("image_url must use HTTP(S)")
    try:
        when = datetime.fromisoformat(scheduled_for.replace("Z", "+00:00"))
    except ValueError:
        raise SchedulingValidationError("scheduled_for must be ISO-8601") from None
    now = datetime.now(ZoneInfo("America/Sao_Paulo"))
    if when.tzinfo is None:
        when = when.replace(tzinfo=now.tzinfo)
    if when <= now:
        raise SchedulingValidationError("scheduled_for must be in the future")
    if database is not None:
        with database._connect() as connection:
            row = connection.execute("SELECT status FROM posts WHERE id = ?", (post_id,)).fetchone()
        if row is None or row["status"] != PostStatus.APPROVED.value:
            raise SchedulingValidationError("Both database and Markdown approvals are required")
        if not database.pillar_is_approved(str(metadata.get("pillar", ""))):
            raise SchedulingValidationError("Pillar is not approved")


def _write_schedule_result(
    path: Path,
    metadata: dict,
    body: str,
    post_id: int,
    status: PostStatus,
    database: Database | None,
) -> None:
    original = path.read_bytes()
    updated = dict(metadata)
    updated["status"] = status.value
    try:
        if database is None:
            write_post_record(path, updated, body)
            return
        with database.transaction() as connection:
            database.transition_post(post_id, status, connection)
            write_post_record(path, updated, body)
    except BaseException:
        if path.exists() and path.read_bytes() != original:
            path.write_bytes(original)
        raise


def create_idea(
    database: Database, research_path: str, pillar: str, angle: str
) -> dict[str, object]:
    """Create an idea only when its research and pillar are eligible."""
    if not database.pillar_is_approved(pillar):
        raise ValueError(f"Pillar {pillar!r} is not approved")
    if not database.research_report_exists(research_path):
        raise ValueError(f"Research report {research_path!r} does not exist")

    idea_id = database.create_idea(angle, pillar, research_path)
    return {"id": idea_id, "research_path": research_path, "pillar": pillar, "angle": angle}


def create_draft(
    database: Database, idea: dict[str, object], pillar: str, path: str | Path
) -> Path:
    """Create a non-approved Markdown draft that retains its research source."""
    persisted_idea = database.create_draft_for_idea(int(idea["id"]), pillar)
    draft_path = Path(path)
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "approved": False,
        "idea_id": persisted_idea["id"],
        "image_url": None,
        "objective": "authority_and_job_opportunities",
        "pillar": pillar,
        "research_path": persisted_idea["research_path"],
        "status": "draft",
        "zernio_post_id": None,
    }
    metadata["post_id"] = persisted_idea["post_id"]
    idea["post_id"] = persisted_idea["post_id"]
    write_post_record(draft_path, metadata, f"Ângulo: {persisted_idea['angle']}")
    return draft_path
