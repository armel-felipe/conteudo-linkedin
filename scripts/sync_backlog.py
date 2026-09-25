#!/usr/bin/env python3
"""Reconcilia `content/backlog.md` com o status real dos topics.

O backlog é escrito à mão pela skill `score-opportunities` e não tem gerador.
Isso permite que ele fique obsoleto quando um topic avança de estado no
`topics_*.yaml` (ex.: `published` pelo Bloco 3) sem que o backlog seja
atualizado. Este script pruna os blocos cujo topic não é mais
`ready_for_research` e reescreve o cabeçalho, preservando a prosa curada.

Não reescreve a prosa dos blocos elegíveis — só remove os obsoletos e ajusta
contagens. Fail-closed: `--check` sai com código 1 se houver divergência.

Uso:
    python scripts/sync_backlog.py --check
    python scripts/sync_backlog.py --write
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BACKLOG_NAME = Path("content") / "backlog.md"
TOPICS_DIR_NAME = Path("research") / "topics"

ELIGIBLE = "ready_for_research"
TOPIC_ID_RE = re.compile(r"topic_[A-Za-z0-9_]+")
SCORE_HEADING_RE = re.compile(r"^##\s+\d")


def load_current_status(topics_dir: Path) -> dict[str, str]:
    """Status de cada topic; arquivo de nome maior vence (como editorial_batch)."""
    status: dict[str, str] = {}
    for path in sorted(topics_dir.glob("topics_*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for topic in document.get("topics", []):
            topic_id = topic.get("id") or topic.get("topic_id")
            if topic_id:
                status[topic_id] = topic.get("status", "")
    return status


def split_backlog(text: str):
    """Divide o backlog em preâmbulo, blocos de topic e seções finais."""
    lines = text.splitlines()
    preamble: list[str] = []
    blocks: list[dict] = []
    tail: list[str] = []
    index = 0

    while index < len(lines) and not lines[index].startswith("## "):
        preamble.append(lines[index])
        index += 1

    current: dict | None = None
    for line in lines[index:]:
        if line.startswith("## "):
            if current:
                blocks.append(current)
            current = {"heading": line, "body": []}
        elif current is None:
            tail.append(line)
        else:
            current["body"].append(line)
    if current:
        blocks.append(current)
    return preamble, blocks, tail


def block_topic_id(block: dict) -> str | None:
    text = "\n".join(block["body"])
    found = TOPIC_ID_RE.search(text)
    return found.group(0) if found else None


def render(block: dict) -> str:
    return "\n".join([block["heading"], *block["body"]]).rstrip()


def _fix_preamble(line: str, ready_count: int) -> str:
    if line.startswith("> Leva de"):
        return re.sub(r"\d+ entram no backlog\.?$", f"{ready_count} entram no backlog.", line)
    return line


def sync(write: bool, root: Path = ROOT) -> int:
    backlog = root / BACKLOG_NAME
    topics_dir = root / TOPICS_DIR_NAME
    status = load_current_status(topics_dir)
    text = backlog.read_text(encoding="utf-8")
    preamble, blocks, tail = split_backlog(text)

    kept, dropped = [], []
    for block in blocks:
        if not SCORE_HEADING_RE.match(block["heading"]):
            kept.append(block)
            continue
        topic_id = block_topic_id(block)
        if topic_id and status.get(topic_id, ELIGIBLE) != ELIGIBLE:
            dropped.append((topic_id, status.get(topic_id, "?")))
        else:
            kept.append(block)

    ready_count = sum(1 for block in kept if SCORE_HEADING_RE.match(block["heading"]))
    updated_preamble = [_fix_preamble(line, ready_count) for line in preamble]
    preamble_changed = updated_preamble != preamble

    for topic_id, current in dropped:
        print(f"obsoleto no backlog: {topic_id} (agora: {current})")
    if preamble_changed and not dropped:
        print(f"cabeçalho desatualizado: {ready_count} tema(s) ready_for_research")

    if not dropped and not preamble_changed:
        print("backlog sincronizado: nenhuma divergência")
        return 0

    if not write:
        print("Rode com --write para corrigir.")
        return 1

    parts = ["\n".join(updated_preamble).rstrip(), ""]
    for block in kept:
        parts.append(render(block))
        parts.append("")
    parts.append("\n".join(tail).strip())
    backlog.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    print(f"backlog atualizado: {ready_count} tema(s) ready_for_research")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="só reporta divergências")
    group.add_argument("--write", action="store_true", help="corrige o backlog")
    args = parser.parse_args()
    return sync(write=args.write)


if __name__ == "__main__":
    raise SystemExit(main())
