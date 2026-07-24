"""Editorial workflow operations that keep research, ideas, and drafts linked."""

import json
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
    account_id: str | None = None,
) -> str:
    """Schedule an approved record once; validation always completes before HTTP."""
    path = Path(markdown_path)
    try:
        metadata, body = read_post_record(path)
    except ValueError as error:
        raise SchedulingValidationError(str(error)) from None
    _recover_pending_schedule_result(path, post_id, metadata, body, database)
    metadata, body = read_post_record(path)
    _validate_schedule(post_id, metadata, body, scheduled_for, confirmed, database, account_id)
    payload: dict[str, object] = {
        "content": body,
        "scheduledFor": scheduled_for,
        "timezone": "America/Sao_Paulo",
        "targets": [{"platform": "linkedin", "accountId": account_id}],
    }
    image_url = metadata.get("image_url")
    if image_url:
        payload["mediaItems"] = [{"url": image_url}]
    try:
        zernio_post_id = client.create_post(payload)
    except Exception:
        _persist_or_record_recovery(path, metadata, body, post_id, PostStatus.FAILED, None, database)
        raise SchedulingError("Scheduling request failed") from None
    if not isinstance(zernio_post_id, str) or not zernio_post_id:
        _persist_or_record_recovery(path, metadata, body, post_id, PostStatus.FAILED, None, database)
        raise SchedulingError("Scheduling request failed")
    metadata["zernio_post_id"] = zernio_post_id
    if not _persist_or_record_recovery(
        path, metadata, body, post_id, PostStatus.SCHEDULED, zernio_post_id, database
    ):
        raise SchedulingError("Scheduling result requires recovery")
    return zernio_post_id


def _validate_schedule(
    post_id: int,
    metadata: dict,
    body: str,
    scheduled_for: str,
    confirmed: bool,
    database: Database | None,
    account_id: str | None,
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
        or not urlparse(image_url).netloc
    ):
        raise SchedulingValidationError("image_url must use HTTP(S)")
    if not isinstance(account_id, str) or not account_id.strip():
        raise SchedulingValidationError("LinkedIn account ID is required")
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


def _persist_or_record_recovery(
    path: Path,
    metadata: dict,
    body: str,
    post_id: int,
    status: PostStatus,
    zernio_post_id: str | None,
    database: Database | None,
) -> bool:
    """Persist each store independently and keep a retry-safe recovery marker.

    A remote request has already been made when this function is called.  A
    partial local write must therefore block another POST until both stores
    agree on the known result.
    """
    updated = dict(metadata)
    updated["status"] = status.value
    updated["zernio_post_id"] = zernio_post_id
    failures: list[BaseException] = []
    if database is not None:
        try:
            database.record_schedule_result(post_id, status, zernio_post_id)
        except BaseException as error:
            failures.append(error)
    try:
        write_post_record(path, updated, body)
    except BaseException as error:
        failures.append(error)
    if not failures:
        return _remove_schedule_recovery(path)
    _write_schedule_recovery(path, post_id, status, zernio_post_id)
    return False


def _recovery_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.schedule-recovery.json")


def _write_schedule_recovery(
    path: Path, post_id: int, status: PostStatus, zernio_post_id: str | None
) -> None:
    """Save only non-sensitive reconciliation data for a partial local write."""
    try:
        _recovery_path(path).write_text(
            json.dumps(
                {
                    "post_id": post_id,
                    "status": status.value,
                    "zernio_post_id": zernio_post_id,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    except OSError:
        # The caller still receives a sanitized failure.  No remote retry is
        # attempted within this invocation.
        pass


def _remove_schedule_recovery(path: Path) -> bool:
    try:
        _recovery_path(path).unlink()
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True


def _recover_pending_schedule_result(
    path: Path, post_id: int, metadata: dict, body: str, database: Database | None
) -> None:
    marker = _recovery_path(path)
    if not marker.exists():
        return
    try:
        saved = json.loads(marker.read_text(encoding="utf-8"))
        status = PostStatus(saved["status"])
        saved_post_id = saved["post_id"]
        zernio_post_id = saved.get("zernio_post_id")
        if saved_post_id != post_id or not isinstance(zernio_post_id, (str, type(None))):
            raise ValueError
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise SchedulingError("Scheduling recovery is required") from None
    if not _persist_or_record_recovery(
        path, metadata, body, post_id, status, zernio_post_id, database
    ):
        raise SchedulingError("Scheduling recovery is required")
    # Recovery records a prior outcome; never send a second POST in this call.
    raise SchedulingError("Previous scheduling attempt recovered; review the post state")


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
