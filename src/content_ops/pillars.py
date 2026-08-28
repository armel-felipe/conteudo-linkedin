"""Transparent, local editorial-pillar proposals derived from post history."""

from __future__ import annotations

import os
import re
import sqlite3
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from content_ops.db import Database


STOP_WORDS = frozenset(
    {
        "a", "as", "da", "das", "de", "do", "dos", "e", "em", "na", "nas",
        "no", "nos", "o", "os", "ou", "para", "por", "um", "uma", "com",
        "sobre", "como", "que", "se", "the", "and", "for", "of", "to",
    }
)
TOPIC_RULES = (
    ("Python e dados", frozenset({"python", "dados", "data"})),
    ("Carreira e oportunidades", frozenset({"carreira", "emprego", "entrevista"})),
    ("IA aplicada", frozenset({"ia", "ai", "llm"})),
)


@dataclass(frozen=True)
class PillarProposal:
    """A proposed pillar with the posts that make its classification auditable."""

    name: str
    count: int
    evidence_ids: tuple[str, ...]


class _PublishedDocumentError(Exception):
    """Signal that a document was replaced before its durability check failed."""

    def __init__(self, original_error: BaseException):
        super().__init__(str(original_error))
        self.original_error = original_error


def propose_pillars(posts: Iterable[str | tuple[str, str]], limit: int = 5) -> list[PillarProposal]:
    """Classify historical posts into no more than ``limit`` ranked pillar proposals."""
    if limit < 0:
        raise ValueError("limit must not be negative")
    limit = min(limit, 5)

    normalized = [_normalize_post(post, index) for index, post in enumerate(posts, start=1)]
    fallback_terms = Counter(
        term for _, text in normalized for term in _useful_terms(text)
    )
    grouped: dict[str, list[str]] = defaultdict(list)
    seen_ids: set[str] = set()
    for post_id, text in normalized:
        if post_id in seen_ids:
            continue
        seen_ids.add(post_id)
        terms = _useful_terms(text)
        name = next(
            (label for label, keywords in TOPIC_RULES if set(terms) & keywords), None
        )
        if name is None:
            name = _fallback_name(terms, fallback_terms)
        if name:
            grouped[name].append(post_id)

    proposals = [
        PillarProposal(name, len(evidence_ids), tuple(evidence_ids))
        for name, evidence_ids in grouped.items()
    ]
    proposals.sort(key=lambda proposal: (-proposal.count, proposal.name))
    return proposals[:limit]


def propose_pillars_from_research(
    database: Database, limit: int = 5
) -> list[PillarProposal]:
    """Propose pillars from captured research reports.

    Reports with a declared ``pillar`` group under that theme. Reports without
    one fall back to their most frequent shared topic term, so the proposal
    set stays auditable: every pillar shows the research paths it came from.
    """
    if limit < 0:
        raise ValueError("limit must not be negative")
    limit = min(limit, 5)

    reports = database.list_research_reports()
    declared: dict[str, list[str]] = defaultdict(list)
    unassigned: list[tuple[str, str]] = []
    for topic, path, pillar, _round_id, _label in reports:
        if pillar:
            declared[pillar].append(path)
        else:
            unassigned.append((path, topic))

    fallback_terms = Counter(
        term for _, topic in unassigned for term in _useful_terms(topic)
    )
    for path, topic in unassigned:
        terms = _useful_terms(topic)
        name = next(
            (label for label, keywords in TOPIC_RULES if set(terms) & keywords), None
        )
        if name is None:
            # Research-driven themes use the dominant shared term as the theme
            # name, so unassigned reports group under a readable topic.
            dominant = max(terms, key=lambda term: (fallback_terms[term], term), default=None)
            name = dominant.capitalize() if dominant else None
        if name:
            declared[name].append(path)

    proposals = [
        PillarProposal(name, len(evidence_ids), tuple(sorted(evidence_ids)))
        for name, evidence_ids in declared.items()
    ]
    proposals.sort(key=lambda proposal: (-proposal.count, proposal.name))
    return proposals[:limit]


def write_pillar_proposals_from_research(
    path: str | Path,
    database: Database,
    limit: int = 5,
) -> list[PillarProposal]:
    """Persist research-driven proposals in SQLite and render the editorial record."""
    proposals = propose_pillars_from_research(database, limit=limit)
    document_path = Path(path)
    _synchronize_document(
        document_path,
        database,
        lambda connection, _: _render_document(
            proposals, database, connection, header="Propostas derivadas de pesquisas capturadas."
        ),
        lambda connection: database.replace_pillars(
            [(proposal.name, proposal.count, proposal.evidence_ids) for proposal in proposals],
            connection,
        ),
    )
    return proposals


def write_pillar_proposals(
    path: str | Path,
    database: Database,
    posts: Iterable[str | tuple[str, str]],
    limit: int = 5,
) -> list[PillarProposal]:
    """Persist transparent proposals in SQLite and render the editorial record."""
    proposals = propose_pillars(posts, limit=limit)
    document_path = Path(path)
    _synchronize_document(
        document_path,
        database,
        lambda connection, _: _render_document(proposals, database, connection),
        lambda connection: database.replace_pillars(
            [(proposal.name, proposal.count, proposal.evidence_ids) for proposal in proposals],
            connection,
        ),
    )
    return proposals


def approve_pillar(path: str | Path, database: Database, name: str) -> None:
    """Approve a recorded proposal in both index and editorial Markdown."""
    document_path = Path(path)
    _synchronize_document(
        document_path,
        database,
        lambda _, document: _approve_document_section(document, name, document_path),
        lambda connection: database.approve_pillar(name, connection=connection),
    )


def _normalize_post(post: str | tuple[str, str], index: int) -> tuple[str, str]:
    if isinstance(post, str):
        return f"post:{index}", post
    post_id, text = post
    return str(post_id), str(text)


def _useful_terms(text: str) -> list[str]:
    return [
        _normalize_token(token)
        for token in re.findall(r"[a-zA-ZÀ-ÿ0-9]+", text.casefold())
        if len(token) > 1 and token not in STOP_WORDS
    ]


def _fallback_name(terms: Sequence[str], frequencies: Counter[str]) -> str | None:
    # Keep terms as observed tokens so ranking uses their actual frequency;
    # dict preserves first occurrence while removing duplicate name candidates.
    selected = sorted(dict.fromkeys(terms), key=lambda term: (-frequencies[term], term))[:2]
    if not selected:
        return None
    if len(selected) == 1:
        return selected[0].capitalize()
    return selected[0].capitalize() + " e " + selected[1]


def _normalize_token(token: str) -> str:
    return {"remotas": "remota"}.get(token, token)


def _approve_document_section(document: str, name: str, path: Path) -> str:
    heading = re.compile(rf"^## {re.escape(name)}$", flags=re.MULTILINE)
    section_start = heading.search(document)
    if section_start is None:
        raise ValueError(f"Pillar {name!r} is not in {path}")
    next_heading = re.compile(r"^## .+$", flags=re.MULTILINE).search(
        document, section_start.end()
    )
    section_end = next_heading.start() if next_heading else len(document)
    section = document[section_start.start() : section_end]
    approval = re.compile(r"^(approved: )(true|false)$", flags=re.MULTILINE)
    match = approval.search(section)
    if match is None:
        raise ValueError(f"Pillar {name!r} has no editable approval field")
    if match.group(2) == "true":
        return document
    updated_section = section[: match.start(2)] + "true" + section[match.end(2) :]
    return document[: section_start.start()] + updated_section + document[section_end:]


def _render_document(
    proposals: Sequence[PillarProposal],
    database: Database,
    connection: sqlite3.Connection,
    header: str = "Propostas geradas do histórico importado.",
) -> str:
    lines = ["# Pilares editoriais", "", header, ""]
    for proposal in proposals:
        lines.extend(
            [
                f"## {proposal.name}",
                f"count: {proposal.count}",
                f"evidence_ids: {', '.join(proposal.evidence_ids)}",
                f"approved: {'true' if database.pillar_is_approved(proposal.name, connection) else 'false'}",
                "",
            ]
        )
    return "\n".join(lines)


def _synchronize_document(
    path: Path,
    database: Database,
    build_document: Callable[[sqlite3.Connection, str], str],
    mutate_database: Callable[[sqlite3.Connection], None],
) -> None:
    """Stage Markdown, then compensate it if the SQLite commit fails.

    Markdown replacement is atomic within its directory, but SQLite and the
    filesystem are separate durability domains. The old document is retained
    until SQLite commits; a failed commit restores it before the error escapes.
    """
    staged: Path | None = None
    published = False
    original: bytes | None = None
    try:
        with database.transaction() as connection:
            original = path.read_bytes() if path.exists() else None
            original_document = original.decode("utf-8") if original is not None else ""
            updated_document = build_document(connection, original_document)
            updated = updated_document.encode("utf-8")
            if updated != original:
                staged = _stage_document(path, updated)
            mutate_database(connection)
            if staged is not None:
                _publish_staged_document(staged, path)
                published = True
    except BaseException as error:
        _discard_staged_document(staged)
        if published or isinstance(error, _PublishedDocumentError):
            try:
                _restore_document(path, original)
            except BaseException as restoration_error:
                raise RuntimeError(
                    f"SQLite synchronization failed and could not restore {path}"
                ) from restoration_error
        if isinstance(error, _PublishedDocumentError):
            raise error.original_error from error
        raise
    finally:
        _discard_staged_document(staged)


def _stage_document(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
    except BaseException:
        _discard_staged_document(temporary_path)
        raise
    return temporary_path


def _publish_staged_document(staged: Path, path: Path) -> None:
    os.replace(staged, path)
    try:
        _fsync_directory(path.parent)
    except BaseException as error:
        raise _PublishedDocumentError(error) from error


def _restore_document(path: Path, original: bytes | None) -> None:
    if original is None:
        path.unlink(missing_ok=True)
        _fsync_directory(path.parent)
        return
    staged = _stage_document(path, original)
    try:
        _publish_staged_document(staged, path)
    finally:
        _discard_staged_document(staged)


def _discard_staged_document(staged: Path | None) -> None:
    if staged is not None:
        staged.unlink(missing_ok=True)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
