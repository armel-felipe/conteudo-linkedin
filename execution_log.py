"""Small, dependency-free JSONL execution logger for the editorial pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Callable
from uuid import uuid4


_SENSITIVE_KEY = re.compile(
    r"(?:auth(?:entication)?[_ -]?token|ct0|cookie|api[_ -]?key|"
    r"authorization|password|passwd|secret|account[_ -]?id|private)"
    r"",
    re.IGNORECASE,
)


def _is_sensitive_key(key: Any) -> bool:
    return isinstance(key, str) and _SENSITIVE_KEY.search(key) is not None


def sanitize_log_value(value: Any, *, _sensitive: bool = False) -> Any:
    """Return a JSON-safe copy with sensitive fields redacted recursively."""

    if _sensitive:
        return "[REDACTED]"
    if isinstance(value, dict):
        return {
            str(key): sanitize_log_value(item, _sensitive=_is_sensitive_key(key))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_log_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [sanitize_log_value(item) for item in sorted(value, key=repr)]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ExecutionLogger:
    def __init__(
        self,
        path: str | Path,
        *,
        run_id: str | None = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self.path = Path(path)
        self.run_id = run_id or str(uuid4())
        self.clock = clock or _utc_now

    def emit(
        self,
        stage: str,
        event: str,
        *,
        route_attempted: Any = (),
        effective_route: str | None = None,
        state: str | None = None,
        duration_ms: int | float | None = None,
        receipt_ref: str | None = None,
        reason: str | None = None,
        details: Any = None,
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "run_id": self.run_id,
            "timestamp": self.clock(),
            "stage": stage,
            "event": event,
            "route_attempted": list(route_attempted),
        }
        optional = {
            "effective_route": effective_route,
            "state": state,
            "duration_ms": duration_ms,
            "receipt_ref": receipt_ref,
            "reason": reason,
            "details": details,
        }
        record.update({key: value for key, value in optional.items() if value is not None})
        sanitized = sanitize_log_value(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(sanitized, ensure_ascii=False, separators=(",", ":")))
            stream.write("\n")
            stream.flush()
        return sanitized

    def start(self, stage: str, **kwargs: Any) -> dict[str, Any]:
        return self.emit(stage, "started", **kwargs)

    def finish(self, stage: str, event: str, **kwargs: Any) -> dict[str, Any]:
        if event not in {"completed", "blocked", "fallback"}:
            raise ValueError("finish event must be completed, blocked or fallback")
        return self.emit(stage, event, **kwargs)
