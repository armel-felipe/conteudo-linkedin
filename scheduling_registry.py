#!/usr/bin/env python3
"""
scheduling_registry.py — Registro e verificação de agendamentos do LinkedIn.

Lê os markers `<!-- agendado: ... -->` de todos os posts em content/ e gera um
registro consolidado que permite:
  1. Verificar conflitos de horário (dois posts no mesmo horário).
  2. Verificar conflitos de conteúdo (mesmo texto agendado duas vezes).
  3. Saber o que está agendado e quando, sem depender de memória de conversa.

Uso:
  python scheduling_registry.py [--check] [--output runs/scheduling-registry.yaml]

Sem --check: gera o registro consolidado.
Com --check: gera o registro e falha (exit 1) se houver conflito de horário
ou de conteúdo, para ser usado como gate antes de agendar.
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
MARKER_RE = re.compile(r"<!--\s*agendado:\s*([^>]+?)\s*-->")


def _first_line(text: str) -> str:
    """Primeira linha não vazia do post, como identificador de conteúdo."""
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("<!--"):
            return line[:120]
    return ""


def _parse_timestamp(raw: str):
    """Converte '2026-09-10T10:00 America/Sao_Paulo' em datetime (naive)."""
    raw = raw.strip()
    # remove o fuso (America/Sao_Paulo) e normaliza
    m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})", raw)
    if not m:
        return None
    return datetime.fromisoformat(m.group(1))


def scan_posts():
    """Varre content/ e retorna lista de posts com marker de agendamento."""
    posts = []
    for folder in ("drafts", "published", "approved", "arquived"):
        dirpath = CONTENT / folder
        if not dirpath.exists():
            continue
        for f in sorted(dirpath.glob("*.md")):
            text = f.read_text(encoding="utf-8")
            markers = MARKER_RE.findall(text)
            if not markers:
                continue
            for marker in markers:
                posts.append({
                    "file": str(f.relative_to(ROOT)),
                    "folder": folder,
                    "topic_id": f.stem,
                    "content_snippet": _first_line(text),
                    "raw_timestamp": marker.strip(),
                    "timestamp": _parse_timestamp(marker),
                })
    return posts


def find_conflicts(posts):
    """Retorna conflitos de horário e de conteúdo."""
    time_conflicts = []
    content_conflicts = []

    # conflito de horário: mesmo timestamp em posts diferentes
    by_time = {}
    for p in posts:
        if p["timestamp"] is None:
            continue
        key = p["timestamp"].isoformat()
        by_time.setdefault(key, []).append(p)
    for key, group in by_time.items():
        if len(group) > 1:
            time_conflicts.append({
                "timestamp": key,
                "posts": [g["topic_id"] for g in group],
            })

    # conflito de conteúdo: mesmo snippet em posts diferentes
    by_content = {}
    for p in posts:
        if not p["content_snippet"]:
            continue
        by_content.setdefault(p["content_snippet"], []).append(p)
    for snippet, group in by_content.items():
        if len(group) > 1:
            content_conflicts.append({
                "content_snippet": snippet,
                "posts": [g["topic_id"] for g in group],
            })

    return time_conflicts, content_conflicts


def build_registry(posts):
    """Monta o registro consolidado."""
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(posts),
        "scheduled": [
            {
                "topic_id": p["topic_id"],
                "folder": p["folder"],
                "file": p["file"],
                "timestamp": p["raw_timestamp"],
                "content_snippet": p["content_snippet"],
            }
            for p in sorted(posts, key=lambda x: x["timestamp"] or datetime.min)
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="falha (exit 1) se houver conflito de horário ou conteúdo")
    parser.add_argument("--output", default="runs/scheduling-registry.yaml",
                        help="caminho do registro de saída")
    args = parser.parse_args()

    posts = scan_posts()
    registry = build_registry(posts)
    time_conflicts, content_conflicts = find_conflicts(posts)

    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_to_yaml(registry), encoding="utf-8")

    print(f"Registro gerado: {out.relative_to(ROOT)}")
    print(f"Posts agendados: {len(posts)}")
    for p in registry["scheduled"]:
        print(f"  - {p['timestamp']}  {p['topic_id']}  ({p['folder']})")

    if time_conflicts:
        print("\nCONFLITOS DE HORÁRIO:")
        for c in time_conflicts:
            print(f"  {c['timestamp']}: {', '.join(c['posts'])}")
    if content_conflicts:
        print("\nCONFLITOS DE CONTEÚDO:")
        for c in content_conflicts:
            print(f"  {c['content_snippet'][:60]}...: {', '.join(c['posts'])}")

    if args.check and (time_conflicts or content_conflicts):
        print("\nFALHA: há conflitos de agendamento. Resolva antes de agendar.")
        sys.exit(1)

    if args.check:
        print("\nOK: sem conflitos de agendamento.")


def _to_yaml(data):
    """Serialização YAML simples (sem dependência externa)."""
    lines = []
    for k, v in data.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                if isinstance(item, dict):
                    lines.append("  -")
                    for ik, iv in item.items():
                        lines.append(f"    {ik}: {_yaml_scalar(iv)}")
                else:
                    lines.append(f"  - {_yaml_scalar(item)}")
        else:
            lines.append(f"{k}: {_yaml_scalar(v)}")
    return "\n".join(lines) + "\n"


def _yaml_scalar(v):
    if isinstance(v, str):
        if ":" in v or v.startswith((" ", "-", "{")):
            return f'"{v}"'
        return v
    return str(v)


if __name__ == "__main__":
    main()
