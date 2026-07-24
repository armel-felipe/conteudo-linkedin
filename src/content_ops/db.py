"""SQLite persistence for the local content workflow index."""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from content_ops.models import ALLOWED_POST_TRANSITIONS, PostStatus


@dataclass(frozen=True)
class Pillar:
    """A proposed editorial pillar stored in the local index."""

    name: str
    approved: bool
    count: int
    evidence_ids: tuple[str, ...]


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
                    count INTEGER NOT NULL DEFAULT 0,
                    evidence_ids TEXT NOT NULL DEFAULT '[]',
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
            pillar_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(pillars)")
            }
            if "count" not in pillar_columns:
                connection.execute(
                    "ALTER TABLE pillars ADD COLUMN count INTEGER NOT NULL DEFAULT 0"
                )
            if "evidence_ids" not in pillar_columns:
                connection.execute(
                    "ALTER TABLE pillars ADD COLUMN evidence_ids TEXT NOT NULL DEFAULT '[]'"
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

    def list_published_posts(self) -> list[tuple[str, str]]:
        """Return stable identifiers and text for imported published posts."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT COALESCE(external_id, CAST(id AS TEXT)), title "
                "FROM posts WHERE status = 'published' ORDER BY id"
            ).fetchall()
        return [(row[0], row[1]) for row in rows]

    def upsert_pillar(self, name: str) -> None:
        """Record a proposal without changing an existing approval decision."""
        with self._connect() as connection:
            connection.execute("INSERT OR IGNORE INTO pillars (name) VALUES (?)", (name,))

    def list_pillars(self) -> list[Pillar]:
        """List proposed pillars in deterministic name order."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT name, approved, count, evidence_ids FROM pillars ORDER BY name"
            ).fetchall()
        return [
            Pillar(
                row["name"],
                bool(row["approved"]),
                row["count"],
                tuple(json.loads(row["evidence_ids"])),
            )
            for row in rows
        ]

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Serialize a write transaction before any approval state is read.

        This only protects SQLite. Callers coordinating another store must use
        their own staged-write and compensation protocol.
        """
        connection = self._connect()
        try:
            self._begin_immediate(connection)
            try:
                yield connection
            except BaseException:
                self._rollback(connection)
                raise
            else:
                try:
                    self._commit(connection)
                except BaseException:
                    self._rollback(connection)
                    raise
        finally:
            connection.close()

    def replace_pillars(
        self,
        pillars: list[tuple[str, int, tuple[str, ...]]],
        connection: sqlite3.Connection | None = None,
    ) -> None:
        """Synchronize the proposal set while retaining approval for matching names.

        Approval belongs to a pillar in the current proposal set. A reproposal
        with the same name preserves its prior approval; absent names are removed
        and linked ideas are detached, so SQLite exactly mirrors the rendered
        editorial record without violating foreign-key integrity.
        """
        names = [name for name, _, _ in pillars]
        if len(names) != len(set(names)):
            raise ValueError("Pillar names must be unique")

        if connection is None:
            with self.transaction() as transaction:
                self.replace_pillars(pillars, transaction)
            return

        for name, count, evidence_ids in pillars:
            connection.execute(
                """
                INSERT INTO pillars (name, count, evidence_ids)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    count = excluded.count,
                    evidence_ids = excluded.evidence_ids
                """,
                (name, count, json.dumps(evidence_ids, ensure_ascii=False)),
            )
        if names:
            placeholders = ", ".join("?" for _ in names)
            missing_clause = f"name NOT IN ({placeholders})"
            connection.execute(
                "UPDATE ideas SET pillar_id = NULL "
                f"WHERE pillar_id IN (SELECT id FROM pillars WHERE {missing_clause})",
                names,
            )
            connection.execute(f"DELETE FROM pillars WHERE {missing_clause}", names)
        else:
            connection.execute("UPDATE ideas SET pillar_id = NULL WHERE pillar_id IS NOT NULL")
            connection.execute("DELETE FROM pillars")

    def approve_pillar(
        self,
        name: str,
        maximum_approved: int = 5,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        """Approve a proposal, rejecting approval number six and beyond."""
        if connection is None:
            with self.transaction() as transaction:
                self.approve_pillar(name, maximum_approved, transaction)
            return

        row = connection.execute(
            "SELECT approved FROM pillars WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Pillar {name!r} does not exist")
        if row["approved"]:
            return
        approved_count = connection.execute(
            "SELECT COUNT(*) FROM pillars WHERE approved = 1"
        ).fetchone()[0]
        if approved_count >= maximum_approved:
            raise ValueError(f"Cannot approve more than {maximum_approved} pillars (at most five)")
        connection.execute("UPDATE pillars SET approved = 1 WHERE name = ?", (name,))

    def pillar_is_approved(
        self, name: str, connection: sqlite3.Connection | None = None
    ) -> bool:
        """Return whether an existing pillar has an approval decision."""
        if connection is None:
            with self._connect() as read_connection:
                return self.pillar_is_approved(name, read_connection)
        row = connection.execute(
            "SELECT approved FROM pillars WHERE name = ?", (name,)
        ).fetchone()
        return bool(row and row["approved"])

    def create_research_report(self, topic: str, path: str) -> int:
        """Record a successfully captured research report."""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO research_reports (topic, path) VALUES (?, ?)
                ON CONFLICT(path) DO UPDATE SET topic = excluded.topic
                """,
                (topic, path),
            )
            return cursor.lastrowid

    def research_report_exists(self, path: str) -> bool:
        """Return whether a report was captured by this local workflow."""
        with self._connect() as connection:
            return connection.execute(
                "SELECT 1 FROM research_reports WHERE path = ?", (path,)
            ).fetchone() is not None

    def create_idea(self, title: str, pillar: str, research_path: str) -> int:
        """Persist an idea linked to one approved pillar and captured report."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT pillars.id AS pillar_id, research_reports.id AS research_report_id
                FROM pillars CROSS JOIN research_reports
                WHERE pillars.name = ? AND research_reports.path = ?
                """,
                (pillar, research_path),
            ).fetchone()
            if row is None:
                raise ValueError("Pillar or research report does not exist")
            cursor = connection.execute(
                """
                INSERT INTO ideas (title, pillar_id, research_report_id)
                VALUES (?, ?, ?)
                """,
                (title, row["pillar_id"], row["research_report_id"]),
            )
            return cursor.lastrowid

    def get_idea(self, idea_id: int) -> dict[str, object]:
        """Return an idea with the links needed to create its draft."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT ideas.id, ideas.title, pillars.name AS pillar, research_reports.path
                FROM ideas
                JOIN pillars ON pillars.id = ideas.pillar_id
                JOIN research_reports ON research_reports.id = ideas.research_report_id
                WHERE ideas.id = ?
                """,
                (idea_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"Idea {idea_id} does not exist or is no longer linked")
        return {
            "id": row["id"],
            "angle": row["title"],
            "pillar": row["pillar"],
            "research_path": row["path"],
        }

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _begin_immediate(connection: sqlite3.Connection) -> None:
        connection.execute("BEGIN IMMEDIATE")

    @staticmethod
    def _commit(connection: sqlite3.Connection) -> None:
        connection.commit()

    @staticmethod
    def _rollback(connection: sqlite3.Connection) -> None:
        connection.rollback()

    @staticmethod
    def _coerce_status(status: str | PostStatus) -> PostStatus:
        return status if isinstance(status, PostStatus) else PostStatus(status)
