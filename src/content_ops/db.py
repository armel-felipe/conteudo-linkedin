"""SQLite persistence for the local content workflow index."""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Iterator
from zoneinfo import ZoneInfo

from content_ops.models import ALLOWED_POST_TRANSITIONS, PostStatus


CURRENT_SCHEMA_VERSION = 4


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
        """Create or migrate the operational schema to the current version."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > CURRENT_SCHEMA_VERSION:
                raise ValueError(
                    f"Database schema version {version} is newer than supported "
                    f"version {CURRENT_SCHEMA_VERSION}"
                )
            migrations = (
                self._migrate_to_v1,
                self._migrate_to_v2,
                self._migrate_to_v3,
                self._migrate_to_v4,
            )
            for target_version in range(version + 1, CURRENT_SCHEMA_VERSION + 1):
                migrations[target_version - 1](connection)
                connection.execute(f"PRAGMA user_version = {target_version}")

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

    def transition_post(
        self,
        post_id: int,
        to_status: PostStatus,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        """Move a post through one permitted workflow transition."""
        destination = self._coerce_status(to_status)
        if connection is None:
            with self.transaction() as transaction:
                self.transition_post(post_id, destination, transaction)
            return

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

    def record_schedule_result(
        self, post_id: int, status: PostStatus, zernio_post_id: str | None
    ) -> None:
        """Persist the result of the single remote scheduling attempt."""
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT status FROM posts WHERE id = ?", (post_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"Post {post_id} does not exist")
            if self._coerce_status(row["status"]) != status:
                self.transition_post(post_id, status, connection)
            connection.execute(
                "UPDATE posts SET zernio_post_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (zernio_post_id, post_id),
            )

    def persist_schedule_intent(
        self, post_id: int, idempotency_key: str, scheduled_for: str, payload: dict
    ) -> None:
        """Durably retain the exact request before it may reach Zernio."""
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT idempotency_key FROM posts WHERE id = ?", (post_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"Post {post_id} does not exist")
            existing = row["idempotency_key"]
            if existing is not None and existing != idempotency_key:
                raise ValueError("Post already has a different idempotency key")
            connection.execute(
                """
                UPDATE posts
                SET idempotency_key = ?, scheduled_for = ?, schedule_payload = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (idempotency_key, scheduled_for, json.dumps(payload, ensure_ascii=False), post_id),
            )

    def schedule_intent(self, post_id: int) -> dict[str, object] | None:
        """Return the persisted remote request, never rebuilding it from edits."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT idempotency_key, scheduled_for, schedule_payload FROM posts WHERE id = ?",
                (post_id,),
            ).fetchone()
        if row is None or not all(row[key] for key in ("idempotency_key", "scheduled_for", "schedule_payload")):
            return None
        try:
            payload = json.loads(row["schedule_payload"])
        except json.JSONDecodeError:
            raise ValueError("Stored scheduling request is invalid") from None
        if not isinstance(payload, dict):
            raise ValueError("Stored scheduling request is invalid")
        return {
            "idempotency_key": row["idempotency_key"],
            "scheduled_for": row["scheduled_for"],
            "payload": payload,
        }

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

    def weekly_status_counts(self, week_start: date) -> dict[str, int]:
        """Count posts scheduled during a Monday-to-Sunday São Paulo week."""
        if week_start.weekday() != 0:
            raise ValueError("week_start must be a Monday")
        timezone = ZoneInfo("America/Sao_Paulo")
        start = datetime.combine(week_start, time.min, timezone)
        end = start + timedelta(days=7)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT status, scheduled_for FROM posts WHERE scheduled_for IS NOT NULL"
            ).fetchall()
        counts: dict[str, int] = {}
        for row in rows:
            try:
                scheduled_for = datetime.fromisoformat(
                    row["scheduled_for"].replace("Z", "+00:00")
                )
            except (AttributeError, ValueError):
                continue
            if scheduled_for.tzinfo is None:
                scheduled_for = scheduled_for.replace(tzinfo=timezone)
            if start <= scheduled_for.astimezone(timezone) < end:
                counts[row["status"]] = counts.get(row["status"], 0) + 1
        return counts

    def scheduled_post(self, post_id: int) -> sqlite3.Row:
        """Return a scheduled post eligible for read-only publication sync."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, status, zernio_post_id FROM posts WHERE id = ?", (post_id,)
            ).fetchone()
        if row is None:
            raise ValueError(f"Post {post_id} does not exist")
        if row["status"] != PostStatus.SCHEDULED.value:
            raise ValueError(f"Post {post_id} is not scheduled")
        if not isinstance(row["zernio_post_id"], str) or not row["zernio_post_id"]:
            raise ValueError(f"Post {post_id} has no Zernio post ID")
        return row

    def post_status(self, post_id: int) -> PostStatus:
        """Return the current local status for an existing post."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM posts WHERE id = ?", (post_id,)
            ).fetchone()
        if row is None:
            raise ValueError(f"Post {post_id} does not exist")
        return self._coerce_status(row["status"])

    def record_publication_sync(
        self,
        post_id: int,
        status: PostStatus,
        platform_post_url: str | None,
        metrics: dict[str, object] | None = None,
        publication_result: dict[str, object] | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        """Store a GET result, mapping terminal remote states from scheduled."""
        if connection is None:
            with self.transaction() as transaction:
                self.record_publication_sync(
                    post_id,
                    status,
                    platform_post_url,
                    metrics,
                    publication_result,
                    transaction,
                )
            return
        row = connection.execute(
            "SELECT status FROM posts WHERE id = ?", (post_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Post {post_id} does not exist")
        if row["status"] != PostStatus.SCHEDULED.value:
            raise ValueError(f"Post {post_id} is not scheduled")
        destination = self._coerce_status(status)
        if destination not in {
            PostStatus.SCHEDULED,
            PostStatus.PUBLISHED,
            PostStatus.FAILED,
        }:
            raise ValueError(f"Unsupported publication sync status: {destination.value}")
        if destination is not PostStatus.SCHEDULED:
            self.transition_post(post_id, destination, connection)
        connection.execute(
            """
            UPDATE posts
            SET platform_post_url = COALESCE(?, platform_post_url),
                metrics = ?,
                publication_result = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                platform_post_url,
                json.dumps(metrics or {}, ensure_ascii=False, sort_keys=True),
                json.dumps(publication_result or {}, ensure_ascii=False, sort_keys=True),
                post_id,
            ),
        )

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

    def create_idea(
        self,
        title: str,
        pillar: str,
        research_path: str,
        connection: sqlite3.Connection | None = None,
    ) -> int:
        """Persist an idea linked to one approved pillar and captured report."""
        if connection is None:
            with self.transaction() as transaction:
                return self.create_idea(title, pillar, research_path, transaction)
        row = connection.execute(
            """
            SELECT pillars.id AS pillar_id, research_reports.id AS research_report_id
            FROM pillars CROSS JOIN research_reports
            WHERE pillars.name = ?
              AND pillars.approved = 1
              AND research_reports.path = ?
            """,
            (pillar, research_path),
        ).fetchone()
        if row is None:
            if connection.execute(
                "SELECT 1 FROM pillars WHERE name = ? AND approved = 0", (pillar,)
            ).fetchone():
                raise ValueError(f"Pillar {pillar!r} is not approved")
            raise ValueError("Pillar or research report does not exist")
        idea_key = hashlib.sha256(
            json.dumps(
                [title, pillar, research_path],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        connection.execute(
            """
            INSERT INTO ideas (
                title, pillar_id, research_report_id, idea_key
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(idea_key) DO NOTHING
            """,
            (title, row["pillar_id"], row["research_report_id"], idea_key),
        )
        idea_row = connection.execute(
            "SELECT id FROM ideas WHERE idea_key = ?", (idea_key,)
        ).fetchone()
        if idea_row is None:
            raise RuntimeError("Could not persist idea")
        return idea_row["id"]

    def create_draft_for_idea(
        self,
        idea_id: int,
        pillar: str,
        connection: sqlite3.Connection | None = None,
    ) -> dict[str, object]:
        """Create a draft post only for the idea's still-approved pillar.

        The supplied pillar is checked against the persisted idea rather than
        trusted from a CLI or workflow caller, preventing cross-pillar drafts.
        """
        if connection is None:
            with self.transaction() as transaction:
                return self.create_draft_for_idea(idea_id, pillar, transaction)
        row = connection.execute(
            """
            SELECT ideas.id, ideas.title, ideas.draft_post_id,
                   pillars.name AS pillar, pillars.approved,
                   research_reports.path AS research_path
            FROM ideas
            JOIN pillars ON pillars.id = ideas.pillar_id
            JOIN research_reports ON research_reports.id = ideas.research_report_id
            WHERE ideas.id = ?
            """,
            (idea_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Idea {idea_id} does not exist or is no longer linked")
        if row["pillar"] != pillar:
            raise ValueError("Draft pillar does not match the idea's pillar")
        if not row["approved"]:
            raise ValueError(f"Pillar {pillar!r} is not approved")
        post_id = row["draft_post_id"]
        created = False
        if post_id is None:
            cursor = connection.execute(
                """
                INSERT INTO posts (title, status, suggested_time, sources)
                VALUES (?, 'draft', NULL, ?)
                """,
                (
                    row["title"],
                    json.dumps(
                        [{"type": "research", "path": row["research_path"]}],
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                ),
            )
            post_id = cursor.lastrowid
            connection.execute(
                "UPDATE ideas SET draft_post_id = ? WHERE id = ?",
                (post_id, idea_id),
            )
            created = True
        elif connection.execute(
            "SELECT 1 FROM posts WHERE id = ?", (post_id,)
        ).fetchone() is None:
            raise ValueError(f"Draft post {post_id} does not exist")
        return {
            "id": row["id"],
            "angle": row["title"],
            "pillar": row["pillar"],
            "research_path": row["research_path"],
            "post_id": post_id,
            "created": created,
        }

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
    def _column_names(
        connection: sqlite3.Connection, table: str
    ) -> set[str]:
        return {
            row["name"] for row in connection.execute(f"PRAGMA table_info({table})")
        }

    @classmethod
    def _add_columns(
        cls,
        connection: sqlite3.Connection,
        table: str,
        definitions: dict[str, str],
    ) -> None:
        existing = cls._column_names(connection, table)
        for name, definition in definitions.items():
            if name not in existing:
                connection.execute(
                    f"ALTER TABLE {table} ADD COLUMN {name} {definition}"
                )

    @classmethod
    def _migrate_to_v1(cls, connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                external_id TEXT,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                zernio_post_id TEXT,
                platform_post_url TEXT,
                idempotency_key TEXT,
                scheduled_for TEXT,
                schedule_payload TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS pillars (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                approved INTEGER NOT NULL DEFAULT 0,
                count INTEGER NOT NULL DEFAULT 0,
                evidence_ids TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS research_reports (
                id INTEGER PRIMARY KEY,
                topic TEXT NOT NULL,
                path TEXT NOT NULL,
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
        cls._add_columns(
            connection,
            "posts",
            {
                "external_id": "TEXT",
                "zernio_post_id": "TEXT",
                "platform_post_url": "TEXT",
                "idempotency_key": "TEXT",
                "scheduled_for": "TEXT",
                "schedule_payload": "TEXT",
                "created_at": "TEXT",
                "updated_at": "TEXT",
            },
        )
        cls._add_columns(
            connection,
            "pillars",
            {
                "count": "INTEGER NOT NULL DEFAULT 0",
                "evidence_ids": "TEXT NOT NULL DEFAULT '[]'",
                "created_at": "TEXT",
            },
        )
        cls._add_columns(
            connection, "research_reports", {"created_at": "TEXT"}
        )
        cls._add_columns(
            connection,
            "ideas",
            {
                "status": "TEXT NOT NULL DEFAULT 'idea'",
                "pillar_id": "INTEGER REFERENCES pillars(id)",
                "research_report_id": "INTEGER REFERENCES research_reports(id)",
                "created_at": "TEXT",
            },
        )
        connection.executescript(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS posts_external_id_unique
                ON posts(external_id);
            CREATE UNIQUE INDEX IF NOT EXISTS pillars_name_unique
                ON pillars(name);
            CREATE UNIQUE INDEX IF NOT EXISTS research_reports_path_unique
                ON research_reports(path);
            """
        )

    @classmethod
    def _migrate_to_v2(cls, connection: sqlite3.Connection) -> None:
        cls._add_columns(
            connection,
            "ideas",
            {
                "idea_key": "TEXT",
                "draft_post_id": "INTEGER REFERENCES posts(id)",
            },
        )
        connection.executescript(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ideas_idea_key_unique
                ON ideas(idea_key);
            CREATE UNIQUE INDEX IF NOT EXISTS ideas_draft_post_unique
                ON ideas(draft_post_id);
            """
        )

    @classmethod
    def _migrate_to_v3(cls, connection: sqlite3.Connection) -> None:
        cls._add_columns(
            connection,
            "posts",
            {
                "metrics": "TEXT NOT NULL DEFAULT '{}'",
                "publication_result": "TEXT",
            },
        )

    @classmethod
    def _migrate_to_v4(cls, connection: sqlite3.Connection) -> None:
        cls._add_columns(
            connection,
            "posts",
            {
                "suggested_time": "TEXT",
                "sources": "TEXT NOT NULL DEFAULT '[]'",
            },
        )

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
