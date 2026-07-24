"""Transparent, local editorial-pillar proposals derived from post history."""

from __future__ import annotations

import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

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


def write_pillar_proposals(
    path: str | Path,
    database: Database,
    posts: Iterable[str | tuple[str, str]],
    limit: int = 5,
) -> list[PillarProposal]:
    """Persist transparent proposals in SQLite and render the editorial record."""
    proposals = propose_pillars(posts, limit=limit)
    document_path = Path(path)
    with database.transaction() as connection:
        database.replace_pillars(
            [(proposal.name, proposal.count, proposal.evidence_ids) for proposal in proposals],
            connection,
        )
        _write_document(document_path, proposals, database, connection)
    return proposals


def approve_pillar(path: str | Path, database: Database, name: str) -> None:
    """Approve a recorded proposal in both index and editorial Markdown."""
    document_path = Path(path)
    document = document_path.read_text(encoding="utf-8")
    updated = _approve_document_section(document, name, document_path)
    with database.transaction() as connection:
        database.approve_pillar(name, connection=connection)
        if updated != document:
            document_path.write_text(updated, encoding="utf-8")


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


def _write_document(
    path: Path,
    proposals: Sequence[PillarProposal],
    database: Database,
    connection: sqlite3.Connection,
) -> None:
    lines = ["# Pilares editoriais", "", "Propostas geradas do histórico importado.", ""]
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
