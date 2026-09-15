import pytest

from scheduling_contract import (
    can_register_timestamp,
    validate_dry_run_events,
    validate_receipt,
    validate_schedule_events,
)


BASE_EVENTS = [
    "approved_file",
    "markdown_converted",
    "browser_attempt",
    "screenshot",
    "visual_route",
]


def schedule_events(route="browser_native"):
    branches = {
        "browser_native": [],
        "image_analyzer": ["image-analyzer:reason=native_failed"],
        "playwright": ["playwright_attempt"],
    }
    return BASE_EVENTS + branches[route] + [
        "date_selected",
        "time_selected",
        "summary_confirmed",
        "advance",
        "final_preview_confirmed",
        "schedule",
        "confirmation",
        "scheduled_list_confirmed",
        "timestamp_registered",
    ]


def valid_receipt(**overrides):
    receipt = {
        "evidence_status": "real_existing_post",
        "route": "browser_native",
        "fallback": "none",
        "requested_timestamp": "2026-09-20T10:00 America/Sao_Paulo",
        "displayed_timestamp": "2026-09-20T10:00 America/Sao_Paulo",
        "date_selected": "pass",
        "time_selected": "pass",
        "summary": "pass",
        "preview": "pass",
        "confirmation": "pass",
        "scheduled_list": "pass",
        "timestamp_registered": "pass",
        "duplicate_created": False,
        "route_attempted": ["browser_native"],
        "browser_attempted": True,
        "route_reasons": {"browser_native": "visual inspection confirmed"},
        "observed_state": {"scheduled_list": "confirmed"},
        "verification_evidence": "scheduled list confirmed after visual route",
        "post_action_confirmation": "confirmed independently in scheduled list",
    }
    receipt.update(overrides)
    return receipt


@pytest.mark.parametrize("route", ["browser_native", "image_analyzer", "playwright"])
def test_visual_first_schedule_is_valid(route):
    assert validate_schedule_events(schedule_events(route), route) is True


def test_visual_first_schedule_does_not_require_playwright():
    assert "playwright_attempt" not in schedule_events("browser_native")
    assert validate_schedule_events(schedule_events("browser_native"), "browser_native") is True


def test_receipt_accepts_browser_first_route_without_playwright():
    receipt = valid_receipt(playwright_attempted=False)
    assert validate_receipt(receipt) is True
    assert can_register_timestamp(
        True,
        True,
        receipt=receipt,
        summary="pass",
        requested_timestamp=receipt["requested_timestamp"],
        displayed_timestamp=receipt["displayed_timestamp"],
        timestamp_registered=True,
        failure_state=None,
    ) is True


def test_playwright_receipt_must_declare_visual_failure():
    receipt = valid_receipt(
        route="playwright",
        route_attempted=["browser_native", "playwright"],
        route_reasons={
            "browser_native": "native_failed",
            "playwright": "read-only diagnostic inspection completed",
        },
        playwright_attempted=True,
        fallback="playwright",
    )
    assert validate_receipt(receipt) is True


def test_image_analyzer_receipt_accepts_explicit_native_failure_evidence():
    receipt = valid_receipt(
        route="image-analyzer",
        fallback="image-analyzer",
        route_attempted=["browser_native", "image-analyzer"],
        route_reasons={
            "browser_native": "native vision failed",
            "image-analyzer": "fallback visual analysis completed",
        },
        image_analyzer_failure=True,
        fallback_reason="native_failed",
    )
    assert validate_receipt(receipt) is True


def test_visual_route_is_primary_and_playwright_only_fallback():
    with pytest.raises(ValueError):
        validate_receipt(valid_receipt(
            route="playwright",
            route_attempted=["playwright"],
            route_reasons={"playwright": "direct mutation"},
        ))


def test_dry_run_stops_before_advance_after_visual_route():
    events = BASE_EVENTS + [
        "date_selected",
        "time_selected",
        "summary_confirmed",
        "blocked_before_advance",
    ]
    assert validate_dry_run_events(events) is True


def test_dry_run_rejects_browser_attempt_without_screenshot():
    events = [
        "approved_file",
        "markdown_converted",
        "browser_attempt",
        "visual_route",
        "date_selected",
        "time_selected",
        "summary_confirmed",
        "blocked_before_advance",
    ]
    with pytest.raises(ValueError):
        validate_dry_run_events(events)
