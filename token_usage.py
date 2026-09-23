"""Aggregate optional token telemetry from execution JSONL logs."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


USAGE_FIELDS = ("input_tokens", "output_tokens", "cached_input_tokens")


def _integer(record: dict[str, Any], field: str) -> int:
    value = record.get(field, 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def _bucket() -> dict[str, int]:
    return {"calls": 0, **{field: 0 for field in USAGE_FIELDS}}


def _add(bucket: dict[str, int], record: dict[str, Any]) -> None:
    bucket["calls"] += 1
    for field in USAGE_FIELDS:
        bucket[field] += _integer(record, field)


def summarize_token_usage(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Return deterministic totals and dimensions for token-bearing records.

    Legacy records remain countable but contribute zero tokens. This makes the
    report useful during gradual rollout without inventing usage values.
    """

    totals = _bucket()
    by_stage: defaultdict[str, dict[str, int]] = defaultdict(_bucket)
    by_model: defaultdict[str, dict[str, int]] = defaultdict(_bucket)
    by_run: defaultdict[str, dict[str, int]] = defaultdict(_bucket)
    for record in records:
        if not isinstance(record, dict):
            continue
        _add(totals, record)
        _add(by_stage[str(record.get("stage", "unknown"))], record)
        _add(by_model[str(record.get("model", "unknown"))], record)
        _add(by_run[str(record.get("run_id", "unknown"))], record)
    return {
        "totals": totals,
        "by_stage": {key: by_stage[key] for key in sorted(by_stage)},
        "by_model": {key: by_model[key] for key in sorted(by_model)},
        "by_run": {key: by_run[key] for key in sorted(by_run)},
    }
