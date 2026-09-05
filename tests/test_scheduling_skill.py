import pytest
from pathlib import Path

from scheduling_contract import (
    can_advance_schedule,
    can_register_timestamp,
    validate_dry_run_events,
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
        "summary_confirmed",
        "advance",
        "final_preview_confirmed",
        "schedule",
        "confirmation",
        "scheduled_list_confirmed",
        "timestamp_registered",
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


@pytest.mark.parametrize(
    "confirmation,scheduled_list",
    [
        ("fail", "fail"),
        ("pass", "pass"),
        ("true", "true"),
        (1, 1),
        ([], []),
        (None, None),
    ],
)
def test_can_register_timestamp_rejects_truthy_failure_values_and_invalid_types(
    confirmation, scheduled_list
):
    assert can_register_timestamp(confirmation, scheduled_list) is False


def valid_registration_gate(**overrides):
    gate = {
        "confirmation": True,
        "scheduled_list": True,
        "receipt": {
            "evidence_status": "real_non_destructive",
            "route": "browser_cdp",
            "fallback": "native",
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
        },
        "summary": "pass",
        "requested_timestamp": "01/09/2026 10:00",
        "displayed_timestamp": "01/09/2026 10:00",
        "timestamp_registered": True,
        "failure_state": None,
    }
    gate.update(overrides)
    return gate


def test_can_register_timestamp_requires_the_complete_explicit_gate():
    gate = valid_registration_gate()
    assert can_register_timestamp(**gate) is True


@pytest.mark.parametrize(
    "change",
    [
        {"receipt": {}},
        {"summary": "fail"},
        {"confirmation": "pass"},
        {"scheduled_list": "pass"},
        {"requested_timestamp": "01/09/2026 11:00"},
        {"displayed_timestamp": "02/09/2026 10:00"},
        {"failure_state": "blocked"},
        {"failure_state": "not_run"},
        {"receipt": {"evidence_status": "simulated"}},
    ],
)
def test_can_register_timestamp_blocks_inconsistent_or_failed_gate(change):
    assert can_register_timestamp(**valid_registration_gate(**change)) is False


def test_reschedule_requires_existing_post_and_complete_new_selection():
    with pytest.raises(ValueError):
        validate_reschedule_events(
            [
                "existing_post_menu",
                "alter_schedule",
                "date_selected",
                "time_selected",
            ],
            "existing_post",
        )


def test_receipt_requires_structured_pass_fields_and_no_sensitive_data():
    receipt = {
        "evidence_status": "real_non_destructive",
        "route": "browser_cdp",
        "fallback": "native",
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
    }
    assert validate_receipt(receipt) is True


@pytest.mark.parametrize(
    "change",
    [
        {"displayed_timestamp": "02/09/2026 10:00"},
        {"summary": "fail"},
        {"date_selected": "fail"},
        {"confirmation": "fail"},
        {"scheduled_list": "fail"},
    ],
)
def test_validate_receipt_rejects_divergence_missing_or_failed_gate(change):
    receipt = {
        "evidence_status": "real_non_destructive",
        "route": "browser_cdp",
        "fallback": "native",
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
    }
    receipt.update(change)
    with pytest.raises(ValueError):
        validate_receipt(receipt)


def test_validate_receipt_rejects_missing_field():
    receipt = {
        "evidence_status": "real_non_destructive",
        "route": "browser_cdp",
        "fallback": "native",
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
    }
    del receipt["preview"]
    with pytest.raises(ValueError):
        validate_receipt(receipt)


@pytest.mark.parametrize("receipt", [None, [], "receipt", 42, True])
def test_validate_receipt_rejects_non_object_root_with_structured_error(receipt):
    with pytest.raises(ValueError, match="receipt must be an object"):
        validate_receipt(receipt)


def test_validate_receipt_rejects_empty_object_as_incomplete():
    with pytest.raises(ValueError, match="incomplete receipt"):
        validate_receipt({})


def test_validate_receipt_accepts_object_root_after_type_boundary():
    receipt = {
        "evidence_status": "real_non_destructive",
        "route": "browser_cdp",
        "fallback": "native",
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
    }
    assert validate_receipt(receipt) is True


@pytest.mark.parametrize("field", ["route", "fallback"])
def test_validate_receipt_rejects_invalid_route_or_fallback(field):
    receipt = {
        "evidence_status": "real_non_destructive",
        "route": "browser_cdp",
        "fallback": "native",
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
    }
    receipt[field] = "invalid"
    with pytest.raises(ValueError):
        validate_receipt(receipt)


@pytest.mark.parametrize("sensitive", ["cookies=abc", "token=abc", "senha", "email@test", "account_id=1", "identificador"])
def test_validate_receipt_rejects_sensitive_text_in_any_field(sensitive):
    receipt = {
        "evidence_status": "real_non_destructive",
        "route": "browser_cdp",
        "fallback": "native",
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
    }
    receipt["summary"] = sensitive
    with pytest.raises(ValueError):
        validate_receipt(receipt)


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

    assert "not_run: criação não executada por segurança" in roadmap
    assert "simulated: contrato/teste" in roadmap
    assert "summary divergence blocks Avançar" in roadmap
    assert "confirmation/list absence blocks registration" in roadmap
    assert "never duplicate" in roadmap
    receipt_fields = (
        "evidence_status: simulated",
        "route: browser_cdp",
        'requested_timestamp: ""',
        'displayed_timestamp: ""',
        "date_selected: not_run",
        "time_selected: not_run",
        "summary: not_run",
        "preview: not_run",
        "confirmation: not_run",
        "scheduled_list: not_run",
        "timestamp_registered: not_run",
        "duplicate_created: false",
    )
    for field in receipt_fields:
        assert field in roadmap
        assert field in report

    sensitive_terms = ("screenshot", "cookie", "account identifier", "private page content")
    assert not any(term in report.lower() for term in sensitive_terms)


def test_round_four_documents_truthful_evidence_and_safe_dry_run_protocol():
    skill = (ROOT / ".agents" / "skills" / "publicar-linkedin" / "SKILL.md").read_text()
    report = (ROOT / ".superpowers" / "sdd" / "scheduling-task-3-report.md").read_text()
    for text in (skill, report):
        for status in ("real_non_destructive", "real_existing_post", "simulated", "not_run"):
            assert status in text
        assert "blocked_before_advance" in text
        assert "não foram executados" in text.lower()
    assert "não confirmar" in report.lower()


def test_dry_run_stops_before_advance():
    assert validate_dry_run_events(
        COMMON_EVENTS
        + [
            "visual_route",
            "date_selected",
            "time_selected",
            "summary_confirmed",
            "blocked_before_advance",
        ]
    ) is True


@pytest.mark.parametrize(
    "event",
    ["advance", "schedule", "confirmation", "scheduled_list_confirmed", "timestamp_registered"],
)
def test_dry_run_rejects_mutating_or_completion_event(event):
    with pytest.raises(ValueError):
        validate_dry_run_events(
            COMMON_EVENTS
            + ["visual_route", "date_selected", "time_selected", "summary_confirmed", event]
        )


@pytest.mark.parametrize(
    "status",
    ["real_non_destructive", "real_existing_post", "simulated", "not_run"],
)
def test_receipt_accepts_each_explicit_evidence_status(status):
    receipt = {
        "evidence_status": status,
        "route": "browser_cdp",
        "fallback": "native",
        "requested_timestamp": "" if status in {"simulated", "not_run"} else "01/09/2026 10:00",
        "displayed_timestamp": "" if status in {"simulated", "not_run"} else "01/09/2026 10:00",
        "date_selected": "not_run" if status in {"simulated", "not_run"} else "pass",
        "time_selected": "not_run" if status in {"simulated", "not_run"} else "pass",
        "summary": "not_run" if status in {"simulated", "not_run"} else "pass",
        "preview": "not_run",
        "confirmation": "not_run",
        "scheduled_list": "not_run",
        "timestamp_registered": "not_run",
        "duplicate_created": False,
    }
    assert validate_receipt(receipt) is True


def test_receipt_rejects_unknown_evidence_status_and_completed_dry_run():
    receipt = {
        "evidence_status": "browser_realish",
        "route": "browser_cdp",
        "fallback": "native",
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
    }
    with pytest.raises(ValueError):
        validate_receipt(receipt)

    receipt["evidence_status"] = "real_non_destructive"
    receipt["confirmation"] = "pass"
    with pytest.raises(ValueError):
        validate_receipt(receipt)


@pytest.mark.parametrize("field", ["confirmation", "scheduled_list", "timestamp_registered"])
def test_dry_run_receipt_cannot_claim_completion_evidence(field):
    receipt = {
        "evidence_status": "simulated",
        "route": "browser_cdp",
        "fallback": "native",
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
    }
    receipt[field] = "pass"
    with pytest.raises(ValueError):
        validate_receipt(receipt)


def test_round_five_report_preserves_existing_schedule_and_states_five_real_scenarios_as_gap():
    report = (ROOT / ".superpowers" / "sdd" / "scheduling-task-3-report.md").read_text()
    assert "## Rodada 5" in report
    assert "agendamento existente" in report.lower()
    assert "timestamp existente não foi alterado" in report.lower()
    assert "cinco cenários reais" in report.lower()
    assert report.lower().count("not_run") >= 5
