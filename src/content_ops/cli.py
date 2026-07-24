"""Command-line entry point for local content operations."""

import argparse
import os
from pathlib import Path
from typing import Sequence


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
    commands = parser.add_subparsers(dest="command")
    history = commands.add_parser("history", help="Import local history from Zernio")
    history.add_subparsers(dest="history_command").add_parser(
        "import", help="Import external posts without publishing"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    load_env(repository_root / ".env")
    parser = build_parser()
    arguments = parser.parse_args(argv)

    if (arguments.command, arguments.history_command) != ("history", "import"):
        return

    required = ("ZERNIO_API_KEY", "ZERNIO_ACCOUNT_ID")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        parser.error(f"Missing required configuration: {', '.join(missing)}")

    from content_ops.db import Database
    from content_ops.history import import_history
    from content_ops.zernio import ZernioClient

    database = Database(repository_root / "data" / "content.db")
    database.initialize()
    imported = import_history(
        ZernioClient(os.environ["ZERNIO_API_KEY"]),
        database,
        os.environ["ZERNIO_ACCOUNT_ID"],
        repository_root / "data" / "imports",
    )
    print(f"Imported {imported} posts.")


if __name__ == "__main__":
    main()
