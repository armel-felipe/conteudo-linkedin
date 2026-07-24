"""Command-line entry point for local content operations."""

import argparse
import os
from pathlib import Path


def load_env(path: Path) -> None:
    """Load simple KEY=VALUE entries without replacing existing environment values."""
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            os.environ.setdefault(key, value.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="contentctl")
    parser.add_subparsers(dest="command").add_parser("history")
    return parser


def main() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    load_env(repository_root / ".env")
    build_parser().parse_args()


if __name__ == "__main__":
    main()
