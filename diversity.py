"""Semantic diversity diagnostics for editorial signals and topics."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml


DIMENSIONS = ("context", "mechanism", "actor", "change_type")
_DIMENSION_WEIGHTS = {
    "context": 0.35,
    "mechanism": 0.35,
    "actor": 0.15,
    "change_type": 0.15,
}


def _values(value: object) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return sorted({item.strip() for item in value if isinstance(item, str) and item.strip()})


def normalize_diversity(value: object) -> dict[str, list[str]]:
    source = value if isinstance(value, dict) else {}
    return {
        dimension: _values(source.get(dimension)) or ["unknown"]
        for dimension in DIMENSIONS
    }


def classify_topic(topic: dict[str, object]) -> dict[str, list[str]]:
    """Return controlled diversity dimensions without inventing classifications."""
    return normalize_diversity(topic.get("diversity"))


def _overlap(left: list[str], right: list[str]) -> bool:
    return bool((set(left) - {"unknown"}) & (set(right) - {"unknown"}))


def topic_distance(
    candidate: dict[str, object],
    recent: list[dict[str, object]],
) -> dict[str, object]:
    """Measure distance from the closest recent topic on a 0-10 scale."""
    candidate_dimensions = classify_topic(candidate)
    scored: list[tuple[float, str, list[str]]] = []
    for item in recent:
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            continue
        item_dimensions = classify_topic(item)
        overlap = [
            dimension
            for dimension in DIMENSIONS
            if _overlap(candidate_dimensions[dimension], item_dimensions[dimension])
        ]
        similarity = sum(_DIMENSION_WEIGHTS[dimension] for dimension in overlap)
        scored.append((similarity, item_id, overlap))

    if not scored:
        return {
            "distance_from_recent_topics": 0,
            "closest_topics": [],
            "overlap": [],
            "explanation": "Histórico insuficiente para calcular distância.",
        }

    closest_similarity = max(item[0] for item in scored)
    closest = sorted(item for item in scored if item[0] == closest_similarity)
    closest_ids = [item[1] for item in closest]
    overlap = closest[0][2]
    distance = round((1 - closest_similarity) * 10, 2)
    if overlap:
        explanation = f"Sobreposição recente em: {', '.join(overlap)}."
    else:
        explanation = "Nenhuma dimensão controlada coincide com os topics mais próximos."
    return {
        "distance_from_recent_topics": distance,
        "closest_topics": closest_ids,
        "overlap": overlap,
        "explanation": explanation,
    }


def concentration_report(topics: list[dict[str, object]]) -> dict[str, object]:
    report: dict[str, object] = {
        "total_topics": len(topics),
        "unknown_count": 0,
    }
    for dimension in DIMENSIONS:
        counter: Counter[str] = Counter()
        for topic in topics:
            values = classify_topic(topic)[dimension]
            counter.update(value for value in values if value != "unknown")
        report[f"by_{dimension}"] = dict(sorted(counter.items()))
    report["unknown_count"] = sum(
        any("unknown" in classify_topic(topic)[dimension] for dimension in DIMENSIONS)
        for topic in topics
    )
    distances = [
        float(topic["diversity_score"]["distance_from_recent_topics"])
        for topic in topics
        if isinstance(topic.get("diversity_score"), dict)
        and isinstance(topic["diversity_score"].get("distance_from_recent_topics"), (int, float))
    ]
    report["distance_average"] = round(sum(distances) / len(distances), 2) if distances else None
    mechanisms = report["by_mechanism"]
    report["alerts"] = []
    if topics and isinstance(mechanisms, dict):
        largest = max(mechanisms.values(), default=0)
        if largest / len(topics) > 0.5:
            report["alerts"].append("Um mecanismo concentra mais de 50% da leva.")
        if len(topics) >= 3 and len(mechanisms) < 3:
            report["alerts"].append("A leva tem menos de três mecanismos distintos.")
    return report


def load_exploratory_questions(path: Path) -> dict[str, list[str]]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    fronts = data.get("frentes")
    if not isinstance(fronts, dict):
        raise ValueError("frentes must be a mapping")
    result: dict[str, list[str]] = {}
    for front_id, front in fronts.items():
        if not isinstance(front, dict):
            raise ValueError(f"front {front_id} must be a mapping")
        questions = front.get("exploratory_questions")
        if not isinstance(questions, list) or not questions or not all(
            isinstance(question, str) and question.strip() for question in questions
        ):
            raise ValueError(f"front {front_id} exploratory_questions must be a non-empty list")
        result[front_id] = questions
    return result
