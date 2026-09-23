"""Deterministic cache identity and safety checks for topic research."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any


def build_research_cache_key(
    topic_id: str,
    window_start: str,
    window_end: str,
    contract_version: str,
    source_config_hash: str,
) -> str:
    payload = {
        "contract_version": contract_version,
        "source_config_hash": source_config_hash,
        "topic_id": topic_id,
        "window_end": window_end,
        "window_start": window_start,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + sha256(encoded).hexdigest()


def cache_is_reusable(metadata: dict[str, Any], *, degraded: bool = False) -> bool:
    """Allow only complete, non-degraded cache entries by default."""

    if not isinstance(metadata, dict) or not metadata.get("cache_key"):
        return False
    if not metadata.get("artifact_path") or not metadata.get("created_at"):
        return False
    if metadata.get("status") not in {"complete", "researched"}:
        return False
    if metadata.get("degraded", False) and not degraded:
        return False
    return True
