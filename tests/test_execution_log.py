import json

from execution_log import ExecutionLogger
from scheduling_contract import validate_receipt_with_log


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
        route_attempted=["playwright", "screenshot+nativa"],
        effective_route="screenshot+nativa",
        state="confirmed",
        duration_ms=12,
        reason="playwright_unavailable",
        details={
            "headers": {"Authorization": "Bearer secret"},
            "nested": [{"api_key": "key"}],
        },
    )
    saved = json.loads(path.read_text().strip())
    assert event == saved
    assert saved["run_id"] == "run-1"
    assert saved["route_attempted"] == [
        "playwright",
        "screenshot+nativa",
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


def test_receipt_validation_can_emit_sanitized_log(tmp_path):
    logger = ExecutionLogger(
        tmp_path / "run.jsonl",
        run_id="receipt-1",
        clock=lambda: "now",
    )
    receipt = {
        "evidence_status": "simulated",
        "route": "stop",
        "fallback": "none",
        "requested_timestamp": "",
        "displayed_timestamp": "",
        "date_selected": "not_run",
        "time_selected": "not_run",
        "summary": "not_run",
        "preview": "not_run",
        "confirmation": "not_run",
        "scheduled_list": "not_run",
        "timestamp_registered": "not_run",
        "duplicate_created": False,
        "route_attempted": ["browser_native"],
        "browser_attempted": True,
        "route_reasons": {"browser_native": "blocked"},
        "observed_state": "ambiguous_mutation",
        "verification_evidence": "state check",
        "post_action_confirmation": "not_run",
    }
    assert validate_receipt_with_log(receipt, logger, receipt_ref="receipt-1") is True
    event = json.loads((tmp_path / "run.jsonl").read_text().splitlines()[-1])
    assert event["event"] == "completed"
    assert event["state"] == "confirmed"
    assert "cookie" not in json.dumps(event).lower()
