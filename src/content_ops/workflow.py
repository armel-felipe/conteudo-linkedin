"""Editorial workflow operations that keep research, ideas, and drafts linked."""

import json
import uuid
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
    _block_if_reconciliation_required(path, post_id, metadata, database)
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
    idempotency_key = _persist_schedule_intent(
        path, post_id, metadata, body, scheduled_for, payload, database
    )
    metadata, body = read_post_record(path)
    return _send_schedule_request(
        path, post_id, metadata, body, payload, idempotency_key, client, database
    )


def reconcile_schedule(
    post_id: int,
    markdown_path: str | Path,
    client: object,
    database: Database,
    account_id: str | None = None,
) -> str:
    """Repeat a recorded uncertain request with its original idempotency key."""
    del account_id  # Account is part of the persisted original request.
    path = Path(markdown_path)
    try:
        metadata, body = read_post_record(path)
    except ValueError as error:
        raise SchedulingValidationError(str(error)) from None
    if not _is_indeterminate(path, post_id, metadata, database):
        raise SchedulingValidationError("Post does not require reconciliation")
    intent = database.schedule_intent(post_id)
    if intent is None:
        raise SchedulingError("Scheduling recovery is required")
    payload = intent["payload"]
    key = intent["idempotency_key"]
    if not isinstance(payload, dict) or not isinstance(key, str):
        raise SchedulingError("Scheduling recovery is required")
    _validate_persisted_idempotency_key(key)
    return _send_schedule_request(path, post_id, metadata, body, payload, key, client, database)


def _send_schedule_request(
    path: Path,
    post_id: int,
    metadata: dict,
    body: str,
    payload: dict[str, object],
    idempotency_key: str,
    client: object,
    database: Database | None,
) -> str:
    try:
        zernio_post_id = client.create_post(payload, idempotency_key)
    except Exception as error:
        from content_ops.zernio import ZernioPreSendError

        # An HTTP response proves the POST reached Zernio, even if it is an
        # error response.  Only the explicit pre-send transport failure is
        # safe to classify as failed; every other outcome requires recovery.
        status = PostStatus.FAILED if isinstance(error, ZernioPreSendError) else PostStatus.INDETERMINATE
        persisted = _persist_or_record_recovery(
            path, metadata, body, post_id, status, None, database
        )
        if not persisted:
            _persist_or_record_recovery(
                path, metadata, body, post_id, PostStatus.INDETERMINATE, None, database
            )
            raise SchedulingError("Scheduling result requires reconciliation") from None
        if status is PostStatus.INDETERMINATE:
            raise SchedulingError("Scheduling result requires reconciliation") from None
        raise SchedulingError("Scheduling request failed") from None
    if not isinstance(zernio_post_id, str) or not zernio_post_id:
        _persist_or_record_recovery(
            path, metadata, body, post_id, PostStatus.INDETERMINATE, None, database
        )
        raise SchedulingError("Scheduling result requires reconciliation")
    if not _persist_or_record_recovery(
        path, metadata, body, post_id, PostStatus.SCHEDULED, zernio_post_id, database
    ):
        _persist_or_record_recovery(
            path, metadata, body, post_id, PostStatus.INDETERMINATE, zernio_post_id, database
        )
        raise SchedulingError("Scheduling result requires reconciliation")
    return zernio_post_id


def _persist_schedule_intent(
    path: Path,
    post_id: int,
    metadata: dict,
    body: str,
    scheduled_for: str,
    payload: dict[str, object],
    database: Database | None,
) -> str:
    """Generate once and retain the exact remote request before any POST."""
    intent = database.schedule_intent(post_id) if database is not None else None
    existing_key = metadata.get("idempotency_key")
    if intent is not None:
        stored_key = intent["idempotency_key"]
        _validate_persisted_idempotency_key(stored_key)
        if existing_key not in (None, stored_key):
            raise SchedulingError("Scheduling recovery is required")
        if intent["scheduled_for"] != scheduled_for or intent["payload"] != payload:
            raise SchedulingError("Stored scheduling request must be reconciled")
        key = stored_key
    else:
        if existing_key is not None:
            _validate_persisted_idempotency_key(existing_key)
        key = existing_key or str(uuid.uuid4())
    updated = dict(metadata)
    updated.update(
        idempotency_key=key,
        scheduled_for=scheduled_for,
        schedule_payload=payload,
    )
    try:
        if database is not None:
            database.persist_schedule_intent(post_id, key, scheduled_for, payload)
        write_post_record(path, updated, body)
    except BaseException:
        # No POST occurred. A durable database intent (if present) lets the next
        # invocation finish the Markdown copy using the same UUID.
        raise SchedulingError("Could not persist scheduling request") from None
    return key


def _validate_persisted_idempotency_key(key: object) -> None:
    """Reject malformed recovery keys before they can be sent over HTTP."""
    if not isinstance(key, str):
        raise SchedulingError("Scheduling recovery is required")
    try:
        uuid.UUID(key)
    except (ValueError, AttributeError, TypeError):
        raise SchedulingError("Scheduling recovery is required") from None


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
    """Persist a remote result, marking uncertainty if either store disagrees."""
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
    _write_schedule_recovery(path, post_id, PostStatus.INDETERMINATE, zernio_post_id)
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


def _is_indeterminate(
    path: Path, post_id: int, metadata: dict, database: Database | None
) -> bool:
    if metadata.get("status") == PostStatus.INDETERMINATE.value or _recovery_path(path).exists():
        return True
    if database is None:
        return False
    with database._connect() as connection:
        row = connection.execute("SELECT status FROM posts WHERE id = ?", (post_id,)).fetchone()
    return bool(row and row["status"] == PostStatus.INDETERMINATE.value)


def _block_if_reconciliation_required(
    path: Path, post_id: int, metadata: dict, database: Database | None
) -> None:
    if _is_indeterminate(path, post_id, metadata, database):
        raise SchedulingError("Scheduling result requires reconciliation")


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
