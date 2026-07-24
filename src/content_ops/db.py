"""SQLite persistence for the local content workflow index."""

import sqlite3
from pathlib import Path

from content_ops.models import ALLOWED_POST_TRANSITIONS, PostStatus


class Database:
    """Small SQLite repository for workflow records."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def initialize(self) -> None:
        """Create the operational schema if it does not exist."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY,
                    external_id TEXT UNIQUE,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS pillars (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    approved INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS research_reports (
                    id INTEGER PRIMARY KEY,
                    topic TEXT NOT NULL,
                    path TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS ideas (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'idea',
                    pillar_id INTEGER REFERENCES pillars(id),
                    research_report_id INTEGER REFERENCES research_reports(id),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def upsert_post(self, external_id: str, title: str, status: str | PostStatus) -> None:
        """Insert or update an externally identified post without duplication."""
        post_status = self._coerce_status(status)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO posts (external_id, title, status)
                VALUES (?, ?, ?)
                ON CONFLICT(external_id) DO UPDATE SET
                    title = excluded.title,
                    status = excluded.status,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (external_id, title, post_status.value),
            )

    def create_post(self, status: str | PostStatus, title: str) -> int:
        """Create a local post and return its database identifier."""
        post_status = self._coerce_status(status)
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO posts (title, status) VALUES (?, ?)",
                (title, post_status.value),
            )
            return cursor.lastrowid

    def transition_post(self, post_id: int, to_status: PostStatus) -> None:
        """Move a post through one permitted workflow transition."""
        destination = self._coerce_status(to_status)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM posts WHERE id = ?", (post_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"Post {post_id} does not exist")

            source = self._coerce_status(row["status"])
            if destination not in ALLOWED_POST_TRANSITIONS.get(source, frozenset()):
                raise ValueError(
                    f"Cannot transition post {post_id} from {source.value} to {destination.value}"
                )

            connection.execute(
                "UPDATE posts SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (destination.value, post_id),
            )

    def count_posts(self) -> int:
        """Return the number of indexed posts."""
        with self._connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM posts").fetchone()[0]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _coerce_status(status: str | PostStatus) -> PostStatus:
        return status if isinstance(status, PostStatus) else PostStatus(status)
