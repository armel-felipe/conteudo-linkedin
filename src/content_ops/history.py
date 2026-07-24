"""Import Zernio history into the local workflow database."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def import_history(client: Any, db: Any, account_id: str, import_dir: str | Path) -> int:
    """Save raw API pages and idempotently index their posts as published."""
    posts = client.list_external_posts(account_id)
    raw_pages = getattr(posts, "pages", [])
    destination = Path(import_dir)
    destination.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

    for page_number, raw_page in enumerate(raw_pages, start=1):
        snapshot = destination / f"zernio-{timestamp}-page-{page_number}.json"
        if not isinstance(raw_page, bytes):
            raise ValueError("Zernio page snapshot is missing raw HTTP bytes")
        snapshot.write_bytes(raw_page)

    imported = 0
    for post in posts:
        post_id = post.get("_id")
        if not post_id:
            raise ValueError("Zernio post is missing _id")
        db.upsert_post(f"linkedin:{post_id}", str(post.get("content", "")), "published")
        imported += 1
    return imported
