"""Deterministic clustering for persisted editorial signals."""

from __future__ import annotations

import argparse
from pathlib import Path
import os
import re
import unicodedata
from typing import Any

import yaml


_STOPWORDS = {
    "a", "ao", "as", "com", "de", "do", "e", "em", "na", "no", "o",
    "os", "para", "por", "que", "se", "sem", "um", "uma",
}


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value.lower())
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return {
        token
        for token in re.findall(r"[a-z0-9]+", without_accents)
        if token not in _STOPWORDS and len(token) > 1
    }


def load_signals(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    signals = data.get("signals")
    if not isinstance(signals, list):
        raise ValueError("input must contain a signals list")
    return signals


def _validate_signal(signal: dict[str, Any]) -> None:
    if not isinstance(signal, dict):
        raise ValueError("signal required fields are missing")
    required = ("id", "title", "pillars", "debate", "evidence")
    if not all(signal.get(field) for field in required):
        raise ValueError("signal required fields are missing")
    if not isinstance(signal["pillars"], list) or not all(isinstance(item, str) for item in signal["pillars"]):
        raise ValueError("signal pillars are required")
    debate = signal["debate"]
    if not isinstance(debate, dict) or not isinstance(debate.get("side_a"), str) or not isinstance(debate.get("side_b"), str):
        raise ValueError("signal debate required fields are missing")
    if not isinstance(signal["evidence"], list):
        raise ValueError("signal evidence is required")


def cluster_signals(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    for signal in signals:
        _validate_signal(signal)
        if signal["id"] in seen:
            raise ValueError(f"duplicate signal id: {signal['id']}")
        seen.add(signal["id"])
    if not signals:
        return []

    parents = list(range(len(signals)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    metadata = []
    for signal in signals:
        debate = signal["debate"]
        metadata.append((set(signal["pillars"]), _tokens(f"{debate['side_a']} {debate['side_b']}")))
    for left in range(len(signals)):
        for right in range(left + 1, len(signals)):
            shared_pillars = metadata[left][0] & metadata[right][0]
            shared_terms = metadata[left][1] & metadata[right][1]
            if shared_pillars and shared_terms:
                union(left, right)

    groups: dict[int, list[dict[str, Any]]] = {}
    for index, signal in enumerate(signals):
        groups.setdefault(find(index), []).append(signal)
    clusters = []
    for group in groups.values():
        ordered = sorted(group, key=lambda item: item["id"])
        clusters.append({
            "id": f"cluster_{ordered[0]['id']}",
            "signal_ids": [item["id"] for item in ordered],
            "pillars": sorted({pillar for item in ordered for pillar in item["pillars"]}),
            "signals": ordered,
        })
    return sorted(clusters, key=lambda item: item["signal_ids"][0])


def _atomic_dump(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    clusters = cluster_signals(load_signals(args.input))
    _atomic_dump(args.output, {"clusters": clusters})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
