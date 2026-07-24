"""Transparent, local editorial-pillar proposals derived from post history."""

from __future__ import annotations

import re
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
        terms = set(_useful_terms(text))
        name = next((label for label, keywords in TOPIC_RULES if terms & keywords), None)
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
    for proposal in proposals:
        database.upsert_pillar(proposal.name)
    _write_document(Path(path), proposals, database)
    return proposals


def approve_pillar(path: str | Path, database: Database, name: str) -> None:
    """Approve a recorded proposal in both index and editorial Markdown."""
    document_path = Path(path)
    document = document_path.read_text(encoding="utf-8")
    heading = f"## {name}\n"
    if heading not in document:
        raise ValueError(f"Pillar {name!r} is not in {document_path}")
    section_pattern = rf"(## {re.escape(name)}\n.*?approved: )false(?=\n|$)"
    updated, replacements = re.subn(section_pattern, r"\1true", document, count=1, flags=re.DOTALL)
    if replacements != 1:
        raise ValueError(f"Pillar {name!r} has no editable approval field")
    database.approve_pillar(name)
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


def _fallback_name(terms: set[str], frequencies: Counter[str]) -> str | None:
    selected = sorted(terms, key=lambda term: (-frequencies[term], term))[:2]
    if not selected:
        return None
    if len(selected) == 1:
        return selected[0].capitalize()
    return selected[0].capitalize() + " e " + selected[1]


def _normalize_token(token: str) -> str:
    return {"remotas": "remota"}.get(token, token)


def _write_document(path: Path, proposals: Sequence[PillarProposal], database: Database) -> None:
    lines = ["# Pilares editoriais", "", "Propostas geradas do histórico importado.", ""]
    for proposal in proposals:
        lines.extend(
            [
                f"## {proposal.name}",
                f"count: {proposal.count}",
                f"evidence_ids: {', '.join(proposal.evidence_ids)}",
                f"approved: {'true' if database.pillar_is_approved(proposal.name) else 'false'}",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
