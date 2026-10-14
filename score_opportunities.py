"""Deterministic weighted scoring for persisted editorial topics."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import os
from typing import Any

import yaml

from diversity import topic_distance


def _validate_weights(weights: dict[str, float]) -> dict[str, float]:
    if not isinstance(weights, dict) or not weights:
        raise ValueError("weights must be a non-empty mapping")
    normalized: dict[str, float] = {}
    for criterion, value in weights.items():
        if not isinstance(criterion, str) or not criterion:
            raise ValueError("weights criteria must be named")
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError("weights values must be non-negative numbers")
        normalized[criterion] = float(value)
    if abs(sum(normalized.values()) - 1.0) > 1e-9:
        raise ValueError("weights must sum to 1.0")
    return normalized


def load_scoring_config(path: Path) -> dict[str, float]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return _validate_weights(data.get("weights"))


def score_topic(topic: dict[str, Any], weights: dict[str, float]) -> dict[str, Any]:
    if not isinstance(topic, dict) or not isinstance(topic.get("id"), str) or not topic["id"]:
        raise ValueError("topic id is required")
    scores = topic.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("criteria scores are required")
    calculated = {}
    weighted_total = 0.0
    for criterion, weight in weights.items():
        value = scores.get(criterion)
        if value is None and criterion == "distance_from_recent_topics":
            value = 0
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 10:
            raise ValueError(f"criteria {criterion} must be a number from 0 to 10")
        calculated[criterion] = value
        weighted_total += float(value) * weight
    result = dict(topic)
    result["scores"] = {**scores, **calculated, "total": round(weighted_total * 10, 2)}
    return result


def score_topics(
    topics: list[dict[str, Any]],
    weights: dict[str, float],
    recent_topics: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result = []
    for topic in topics:
        topic_id = topic.get("id") if isinstance(topic, dict) else None
        if topic_id in seen:
            raise ValueError(f"duplicate topic id: {topic_id}")
        seen.add(topic_id)
        prepared = dict(topic)
        if recent_topics is not None:
            distance = topic_distance(prepared, recent_topics)
            prepared["diversity_score"] = distance
            prepared["scores"] = {
                **(prepared.get("scores") or {}),
                "distance_from_recent_topics": distance["distance_from_recent_topics"],
            }
        result.append(score_topic(prepared, weights))
    return result


def run_scoring(topics: list[dict[str, Any]], weights: dict[str, float]) -> list[dict[str, Any]]:
    """Score an explicit sample and return a deterministic ranking."""
    normalized = _validate_weights(weights)
    for topic in topics:
        scores = topic.get("scores") if isinstance(topic, dict) else None
        criteria = set(scores) - {"total"} if isinstance(scores, dict) else set()
        allowed_missing = {"distance_from_recent_topics"}
        if criteria - allowed_missing != set(normalized) - allowed_missing:
            raise ValueError("weights criteria must match topic criteria")
    scored = score_topics(topics, normalized)
    return sorted(scored, key=lambda topic: (-topic["scores"]["total"], topic["id"]))


def _atomic_dump(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--recent-topics", action="append", type=Path, default=[])
    args = parser.parse_args(argv)
    source = yaml.safe_load(args.input.read_text(encoding="utf-8")) or {}
    topics = source.get("topics")
    if not isinstance(topics, list):
        raise ValueError("input must contain a topics list")
    recent_topics: list[dict[str, Any]] | None = None
    if args.recent_topics:
        recent_topics = []
        for recent_path in args.recent_topics:
            recent_document = yaml.safe_load(recent_path.read_text(encoding="utf-8")) or {}
            recent_items = recent_document.get("topics")
            if not isinstance(recent_items, list):
                raise ValueError("recent topics input must contain a topics list")
            recent_topics.extend(recent_items)
    scored = score_topics(topics, load_scoring_config(args.config), recent_topics=recent_topics)
    _atomic_dump(args.output, {"topics": scored})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
