"""Read-only publication synchronization and weekly operational reporting."""

from datetime import date
from typing import Any

from content_ops.db import Database


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


def sync_published_post(client: Any, db: Database, post_id: int) -> bool:
    """Use one GET result to mark a scheduled post published when confirmed."""
    post = db.scheduled_post(post_id)
    response = client.get_post(post["zernio_post_id"])
    payload = response.get("data", response) if isinstance(response, dict) else {}
    if not isinstance(payload, dict):
        payload = {}
    status = payload.get("status")
    published = isinstance(status, str) and status.lower() == "published"
    platform_post_url = payload.get("platformPostUrl")
    if not isinstance(platform_post_url, str) or not platform_post_url:
        platform_post_url = None
    db.record_publication_sync(post_id, published, platform_post_url)
    return published
