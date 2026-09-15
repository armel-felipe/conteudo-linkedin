import pytest

from scheduling_contract import (
    can_advance_schedule,
    can_register_timestamp,
    validate_dry_run_events,
    validate_receipt,
    validate_reschedule_events,
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


def valid_registration_gate(**overrides):
    receipt = {
        "evidence_status": "real_existing_post",
        "route": "browser_native",
        "fallback": "none",
        "requested_timestamp": "01/09/2026 10:00",
        "displayed_timestamp": "01/09/2026 10:00",
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
    gate = {
        "confirmation": True,
        "scheduled_list": True,
        "receipt": receipt,
        "summary": "pass",
        "requested_timestamp": "01/09/2026 10:00",
        "displayed_timestamp": "01/09/2026 10:00",
        "timestamp_registered": True,
        "failure_state": None,
    }
    gate.update(overrides)
    return gate


def simulated_receipt(**overrides):
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
        "route_reasons": {"browser_native": "visual route unavailable"},
        "observed_state": {"state": "not_run"},
        "verification_evidence": "contract-only evidence; no browser mutation",
        "post_action_confirmation": "not_run",
    }
    receipt.update(overrides)
    return receipt


def real_receipt(**overrides):
    receipt = {
        "evidence_status": "real_non_destructive",
        "route": "browser_native",
        "fallback": "none",
        "requested_timestamp": "01/09/2026 10:00",
        "displayed_timestamp": "01/09/2026 10:00",
        "date_selected": "pass",
        "time_selected": "pass",
        "summary": "pass",
        "preview": "not_run",
        "confirmation": "not_run",
        "scheduled_list": "not_run",
        "timestamp_registered": "not_run",
        "duplicate_created": False,
        "route_attempted": ["browser_native"],
        "browser_attempted": True,
        "route_reasons": {"browser_native": "visual inspection completed"},
        "observed_state": {"scheduled_list": "not confirmed"},
        "verification_evidence": "visual route evidence",
        "post_action_confirmation": "confirmed independently in scheduled list",
    }
    receipt.update(overrides)
    return receipt


@pytest.mark.parametrize("route", ["browser_native", "image_analyzer", "playwright"])
def test_validate_schedule_events_accepts_valid_routes(route):
    assert validate_schedule_events(schedule_events(route), route) is True


def test_visual_route_is_primary_without_playwright():
    events = schedule_events("browser_native")
    assert "playwright_attempt" not in events
    assert validate_schedule_events(events, "browser_native") is True


def test_schedule_rejects_missing_screenshot_or_bad_timestamp_order():
    events = schedule_events()
    events.remove("screenshot")
    with pytest.raises(ValueError):
        validate_schedule_events(events, "browser_native")

    events = schedule_events()
    events.remove("timestamp_registered")
    events.insert(events.index("scheduled_list_confirmed"), "timestamp_registered")
    with pytest.raises(ValueError):
        validate_schedule_events(events, "browser_native")


def test_playwright_only_mutation_is_rejected():
    with pytest.raises(ValueError):
        validate_schedule_events(
            [
                "approved_file",
                "markdown_converted",
                "playwright_attempt",
                "visual_route",
                *schedule_events("playwright")[6:],
            ],
            "playwright",
        )


def test_unreadable_image_stops_before_schedule():
    events = [
        "approved_file",
        "markdown_converted",
        "browser_attempt",
        "screenshot",
        "image-analyzer:reason=unreadable_image",
        "stop",
    ]
    assert validate_schedule_events(events, "unreadable_image") is True
    with pytest.raises(ValueError):
        validate_schedule_events(events + ["schedule"], "unreadable_image")


def test_reschedule_requires_existing_post_and_visual_attempt():
    events = [
        "browser_attempt",
        "existing_post_menu",
        "alter_schedule",
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
    assert validate_reschedule_events(
        events, "existing_post", effective_route="browser_native", fallback="none"
    ) is True

    with pytest.raises(ValueError):
        validate_reschedule_events(events[1:], "existing_post", effective_route="browser_native", fallback="none")


def test_can_register_timestamp_requires_complete_explicit_gate():
    assert can_register_timestamp(**valid_registration_gate()) is True
    assert can_register_timestamp(False, True) is False
    assert can_register_timestamp(True, False) is False
    assert can_register_timestamp("pass", "pass") is False


@pytest.mark.parametrize("change", [
    {"receipt": {}},
    {"summary": "fail"},
    {"confirmation": "pass"},
    {"scheduled_list": "pass"},
    {"requested_timestamp": "01/09/2026 11:00"},
    {"displayed_timestamp": "02/09/2026 10:00"},
    {"failure_state": "blocked"},
    {"failure_state": "not_run"},
    {"receipt": {"evidence_status": "simulated"}},
])
def test_can_register_timestamp_blocks_bad_gate(change):
    assert can_register_timestamp(**valid_registration_gate(**change)) is False


@pytest.mark.parametrize("status", ["real_non_destructive", "simulated", "not_run"])
def test_can_register_timestamp_rejects_non_mutating_evidence(status):
    gate = valid_registration_gate()
    gate["receipt"]["evidence_status"] = status
    if status != "real_non_destructive":
        gate["receipt"].update({
            "requested_timestamp": "",
            "displayed_timestamp": "",
            "date_selected": "not_run",
            "time_selected": "not_run",
            "summary": "not_run",
            "preview": "not_run",
            "confirmation": "not_run",
            "scheduled_list": "not_run",
            "timestamp_registered": "not_run",
            "post_action_confirmation": "not_run",
        })
    assert can_register_timestamp(**gate) is False


def test_can_advance_and_register_match_timestamps():
    assert can_advance_schedule("10:00", "10:00") is True
    assert can_advance_schedule("10:00", "11:00") is False


def test_receipt_accepts_browser_first_without_playwright():
    assert validate_receipt(real_receipt(playwright_attempted=False)) is True


def test_receipt_rejects_missing_field():
    receipt = real_receipt()
    receipt.pop("preview")
    with pytest.raises(ValueError, match="incomplete receipt"):
        validate_receipt(receipt)


def test_receipt_rejects_route_history_that_does_not_follow_visual_first():
    receipt = real_receipt()
    receipt["route_attempted"] = ["playwright", "browser_native"]
    with pytest.raises(ValueError):
        validate_receipt(receipt)


def test_receipt_requires_post_action_confirmation_for_real_evidence():
    receipt = real_receipt(evidence_status="real_existing_post")
    receipt["post_action_confirmation"] = "not_run"
    with pytest.raises(ValueError):
        validate_receipt(receipt)


def test_stop_receipt_requires_verification_evidence():
    receipt = simulated_receipt()
    assert validate_receipt(receipt) is True
    receipt.pop("verification_evidence")
    with pytest.raises(ValueError):
        validate_receipt(receipt)


def test_playwright_route_requires_visual_failure_and_attempt_evidence():
    receipt = real_receipt(
        route="playwright",
        fallback="playwright",
        route_attempted=["browser_native", "playwright"],
        route_reasons={
            "browser_native": "native_failed",
            "playwright": "read-only diagnostic inspection completed",
        },
        browser_attempted=True,
        playwright_attempted=True,
    )
    assert validate_receipt(receipt) is True


def test_dry_run_stops_before_advance_after_visual_route():
    events = BASE_EVENTS + [
        "date_selected",
        "time_selected",
        "summary_confirmed",
        "blocked_before_advance",
    ]
    assert validate_dry_run_events(events) is True


def test_dry_run_rejects_missing_screenshot():
    with pytest.raises(ValueError):
        validate_dry_run_events(
            [
                "approved_file",
                "markdown_converted",
                "browser_attempt",
                "visual_route",
                "date_selected",
                "time_selected",
                "summary_confirmed",
                "blocked_before_advance",
            ]
        )


@pytest.mark.parametrize("event", ["advance", "schedule", "confirmation", "scheduled_list_confirmed", "timestamp_registered"])
def test_dry_run_rejects_mutating_or_completion_event(event):
    with pytest.raises(ValueError):
        validate_dry_run_events(
            BASE_EVENTS + ["date_selected", "time_selected", "summary_confirmed", event]
        )


@pytest.mark.parametrize("sensitive", ["cookies=abc", "token=abc", "senha", "email@test", "account_id=1", "identificador", "secret=abc", "API_KEY=abc"])
def test_receipt_rejects_sensitive_text(sensitive):
    receipt = real_receipt()
    receipt["summary"] = sensitive
    with pytest.raises(ValueError):
        validate_receipt(receipt)


@pytest.mark.parametrize("sensitive_key", ["secret", "API_KEY", "authorization-header"])
def test_receipt_rejects_sensitive_nested_keys(sensitive_key):
    receipt = real_receipt()
    receipt["observed_state"] = {"nested": [{sensitive_key: "redacted"}]}
    with pytest.raises(ValueError, match="sensitive receipt value"):
        validate_receipt(receipt)
