import json

from execution_log import ExecutionLogger


def test_sanitizes_nested_secrets_and_writes_jsonl(tmp_path):
    path = tmp_path / "run.jsonl"
    logger = ExecutionLogger(
        path,
        run_id="run-1",
        clock=lambda: "2026-09-06T00:00:00Z",
    )
    event = logger.emit(
        "browser",
        "fallback",
        route_attempted=["mcp_chrome_devtools", "playwright_fallback"],
        effective_route="playwright_fallback",
        state="confirmed",
        duration_ms=12,
        reason="mcp_unavailable",
        details={
            "headers": {"Authorization": "Bearer secret"},
            "nested": [{"api_key": "key"}],
        },
    )
    saved = json.loads(path.read_text().strip())
    assert event == saved
    assert saved["run_id"] == "run-1"
    assert saved["route_attempted"] == [
        "mcp_chrome_devtools",
        "playwright_fallback",
    ]
    assert saved["details"]["headers"]["Authorization"] == "[REDACTED]"
    assert saved["details"]["nested"][0]["api_key"] == "[REDACTED]"


def test_start_and_finish_emit_required_lifecycle_events(tmp_path):
    logger = ExecutionLogger(
        tmp_path / "run.jsonl",
        run_id="run-2",
        clock=lambda: "now",
    )
    logger.start("research")
    logger.finish(
        "research",
        "blocked",
        state="unconfigured",
        reason="source_unavailable",
    )
    events = [
        json.loads(line)
        for line in (tmp_path / "run.jsonl").read_text().splitlines()
    ]
    assert [event["event"] for event in events] == ["started", "blocked"]
