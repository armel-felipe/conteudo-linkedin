import pytest
from pathlib import Path

from scheduling_contract import (
    can_advance_schedule,
    can_register_timestamp,
    validate_receipt,
    validate_reschedule_events,
    validate_schedule_events,
)


ROOT = Path(__file__).resolve().parents[1]


COMMON_EVENTS = [
    "approved_file",
    "markdown_converted",
    "playwright_attempt",
]


def scheduled_events(route="playwright"):
    branch = {
        "playwright": [],
        "no_native_vision": ["image-analyzer:reason=no_native_vision"],
        "native_failed": [
            "screenshot_fallback_if_needed",
            "image-analyzer:reason=native_failed",
        ],
    }[route]
    return COMMON_EVENTS + branch + [
        "visual_route",
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


@pytest.mark.parametrize("route", ["playwright", "no_native_vision", "native_failed"])
def test_validate_schedule_events_accepts_valid_routes(route):
    assert validate_schedule_events(scheduled_events(route), route) is True


def test_playwright_success_does_not_require_screenshot_fallback():
    events = scheduled_events("playwright")
    assert "screenshot_fallback_if_needed" not in events
    assert validate_schedule_events(events, "playwright") is True


def test_validate_schedule_events_rejects_missing_gate_and_bad_timestamp_order():
    events = scheduled_events()
    events.remove("summary_confirmed")
    with pytest.raises(ValueError):
        validate_schedule_events(events, "playwright")

    events = scheduled_events()
    events.insert(events.index("schedule"), "schedule")
    with pytest.raises(ValueError):
        validate_schedule_events(events, "playwright")

    events = scheduled_events()
    events.remove("timestamp_registered")
    events.insert(events.index("scheduled_list_confirmed"), "timestamp_registered")
    with pytest.raises(ValueError):
        validate_schedule_events(events, "playwright")


def test_validate_schedule_events_rejects_individual_fallback_misuse():
    events = scheduled_events("playwright")
    events.insert(3, "screenshot_fallback_if_needed")
    with pytest.raises(ValueError):
        validate_schedule_events(events, "playwright")

    events = scheduled_events("no_native_vision")
    events.insert(3, "screenshot_fallback_if_needed")
    with pytest.raises(ValueError):
        validate_schedule_events(events, "no_native_vision")


def test_unreadable_image_stops_before_schedule():
    events = COMMON_EVENTS + [
        "screenshot_fallback_if_needed",
        "image-analyzer:reason=unreadable_image",
        "stop",
    ]
    assert validate_schedule_events(events, "unreadable_image") is True

    with pytest.raises(ValueError):
        validate_schedule_events(events + ["schedule"], "unreadable_image")


def test_validate_reschedule_events_accepts_existing_post_flow():
    events = [
        "existing_post_menu",
        "alter_schedule",
        "date_selected",
        "time_selected",
    ]
    assert validate_reschedule_events(events, "existing_post") is True


@pytest.mark.parametrize(
    "events",
    [
        ["new_composer", "alter_schedule", "date_selected", "time_selected"],
        ["existing_post_menu", "alter_schedule", "time_selected", "date_selected"],
        ["existing_post_menu", "alter_schedule", "date_selected", "date_selected", "time_selected"],
    ],
)
def test_validate_reschedule_events_rejects_duplicate_or_invalid_existing_post_flow(events):
    with pytest.raises(ValueError):
        validate_reschedule_events(events, "existing_post")


def test_behavioral_helper_blocks_divergent_summary_and_missing_confirmation_or_list():
    assert can_advance_schedule("01/09/2026 10:00", "01/09/2026 10:00") is True
    assert can_advance_schedule("01/09/2026 10:00", "02/09/2026 10:00") is False
    assert can_register_timestamp(True, True) is True
    assert can_register_timestamp(False, True) is False
    assert can_register_timestamp(True, False) is False


def test_reschedule_requires_existing_post_and_complete_new_selection():
    assert validate_reschedule_events(
        [
            "existing_post_menu",
            "alter_schedule",
            "date_selected",
            "time_selected",
        ],
        "existing_post",
    ) is True


def test_receipt_requires_structured_pass_fields_and_no_sensitive_data():
    receipt = {
        "route": "browser",
        "fallback": "CDP",
        "requested_timestamp": "01/09/2026 10:00",
        "displayed_timestamp": "01/09/2026 10:00",
        "date_selected": "pass",
        "time_selected": "pass",
        "summary": "pass",
        "preview": "pass",
        "confirmation": "pass",
        "scheduled_list": "pass",
        "duplicate_created": False,
    }
    assert validate_receipt(receipt) is True


def test_manual_scheduling_matrix_and_receipt_are_non_sensitive_and_complete():
    roadmap = (ROOT / "docs" / "roadmap.md").read_text()
    report = (ROOT / ".superpowers" / "sdd" / "scheduling-task-3-report.md").read_text()

    expected_cases = (
        "new schedule with different date and time",
        "new schedule for today with explicit date and time",
        "reschedule existing post with same time and different date",
        "wrong summary detected before Avançar",
        "scheduled post missing from the scheduled list",
    )
    for case in expected_cases:
        assert case in roadmap

    assert "executado: real" in roadmap
    assert "simulado: não destrutivo" in roadmap
    assert "summary divergence blocks Avançar" in roadmap
    assert "confirmation/list absence blocks registration" in roadmap
    assert "never duplicate" in roadmap
    receipt_fields = (
        "route: browser",
        "fallback: CDP",
        'requested_timestamp: "01/09/2026 10:00"',
        'displayed_timestamp: "01/09/2026 10:00"',
        "date_selected: pass",
        "time_selected: pass",
        "summary: pass",
        "preview: pass",
        "confirmation: pass",
        "scheduled_list: pass",
        "duplicate_created: false",
    )
    for field in receipt_fields:
        assert field in roadmap
        assert field in report

    sensitive_terms = ("screenshot", "cookie", "account identifier", "private page content")
    assert not any(term in report.lower() for term in sensitive_terms)
