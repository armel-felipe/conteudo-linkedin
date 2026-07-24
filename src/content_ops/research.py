"""Capture external recent-research output without editorial interpretation."""

import shlex
import subprocess
from pathlib import Path


def capture_research(topic: str, command: str, target_path: str | Path) -> Path:
    """Run the configured research command and persist its stdout unchanged.

    The command is intentionally configured outside the repository.  A failed
    command never creates or replaces a report, so callers cannot accidentally
    build ideas from partial research.
    """
    arguments = shlex.split(command)
    if not arguments:
        raise ValueError("LAST30DAYS_COMMAND is required")

    result = subprocess.run(
        [*arguments, topic], text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"Research command failed with exit code {result.returncode}")

    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.stdout, encoding="utf-8")
    return path
