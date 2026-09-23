#!/usr/bin/env python3
"""Print aggregated token telemetry from one or more JSONL execution logs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from token_usage import summarize_token_usage


def _records(paths: list[str]):
    for raw_path in paths:
        path = Path(raw_path)
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise SystemExit(f"invalid JSON in {path}:{line_number}: {error}") from error
            if isinstance(value, dict):
                yield value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("logs", nargs="+", help="execution JSONL files")
    args = parser.parse_args()
    print(json.dumps(summarize_token_usage(_records(args.logs)), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
