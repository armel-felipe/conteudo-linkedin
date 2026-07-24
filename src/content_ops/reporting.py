"""Read-only publication synchronization and weekly operational reporting."""

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from content_ops.db import Database
from content_ops.markdown import read_post_record, write_post_record
from content_ops.models import PostStatus


def weekly_report(db: Database, week_start: date) -> str:
    """Render status counts and the weekly two-post publishing cadence."""
    counts = db.weekly_status_counts(week_start)
    week_end = week_start.fromordinal(week_start.toordinal() + 6)
    lines = [f"Semana: {week_start.isoformat()} a {week_end.isoformat()}"]
    for status in sorted(counts):
        lines.append(f"{status}: {counts[status]}")
    cadence = counts.get("scheduled", 0) + counts.get("published", 0)
    lines.append(f"Cadência: {cadence}/2")
    return "\n".join(lines)


def sync_published_post(
    client: Any,
    db: Database,
    post_id: int,
    markdown_path: str | Path,
) -> bool:
    """Apply one GET result to SQLite and Markdown as one recoverable operation."""
    post = db.scheduled_post(post_id)
    response = client.get_post(post["zernio_post_id"])
    payload = response.get("data", response) if isinstance(response, dict) else {}
    if not isinstance(payload, dict):
        payload = {}
    status = payload.get("status")
    normalized_status = status.lower() if isinstance(status, str) else ""
    if normalized_status == PostStatus.PUBLISHED.value:
        local_status = PostStatus.PUBLISHED
    elif normalized_status == PostStatus.FAILED.value:
        local_status = PostStatus.FAILED
    else:
        local_status = PostStatus.SCHEDULED
    published = local_status is PostStatus.PUBLISHED
    platform_post_url = payload.get("platformPostUrl")
    if not isinstance(platform_post_url, str) or not platform_post_url:
        platform_post_url = None
    metrics = _publication_metrics(payload)
    publication_result = {
        "status": status if isinstance(status, str) else "unknown",
        "synced_at": datetime.now(UTC).isoformat(),
    }
    if platform_post_url:
        publication_result["published_url"] = platform_post_url

    path = Path(markdown_path)
    metadata, body = read_post_record(path)
    if metadata.get("post_id") not in (None, post_id):
        raise ValueError("Markdown record belongs to another post")
    if metadata.get("status") != "scheduled":
        raise ValueError(f"Markdown record for post {post_id} is not scheduled")
    original = path.read_bytes()
    updated = dict(metadata)
    updated["status"] = local_status.value
    updated["published_url"] = platform_post_url or metadata.get("published_url")
    updated["metrics"] = metrics
    updated["publication_result"] = publication_result
    recovery_path = _publication_recovery_path(path)
    try:
        with db.transaction() as connection:
            db.record_publication_sync(
                post_id,
                local_status,
                platform_post_url,
                metrics,
                publication_result,
                connection,
            )
            write_post_record(path, updated, body)
    except BaseException:
        if path.exists() and path.read_bytes() != original:
            try:
                path.write_bytes(original)
            except OSError:
                recovery_path.write_text(
                    json.dumps(
                        {
                            "post_id": post_id,
                            "operation": "publication_sync",
                        },
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )
        raise
    recovery_path.unlink(missing_ok=True)
    return published


def _publication_metrics(payload: dict[str, Any]) -> dict[str, int | float]:
    """Retain only numeric aggregate metrics supplied by the read-only API."""
    candidate = payload.get("metrics", payload.get("analytics", {}))
    if not isinstance(candidate, dict):
        return {}
    return {
        str(key): value
        for key, value in sorted(candidate.items())
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }


def _publication_recovery_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.publication-sync-recovery.json")
