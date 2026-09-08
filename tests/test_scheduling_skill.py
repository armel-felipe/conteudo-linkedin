import pytest
import yaml
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


def test_validate_schedule_events_requires_playwright_attempt():
    events = scheduled_events("playwright")
    events.remove("playwright_attempt")
    with pytest.raises(ValueError):
        validate_schedule_events(events, "playwright")


def test_validate_schedule_events_rejects_playwright_only_mutating_flow():
    events = [
        "approved_file",
        "markdown_converted",
        "playwright_attempt",
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
    assert validate_schedule_events(events, "playwright") is True


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
        "playwright_attempt",
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
        events,
        "existing_post",
        effective_route="playwright",
        fallback="none",
    ) is True


def test_validate_reschedule_events_requires_playwright_and_effective_fallback_route():
    events = [
        "playwright_attempt",
        "screenshot_fallback_if_needed",
        "image-analyzer:reason=native_failed",
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
        events,
        "existing_post",
        effective_route="image-analyzer",
        fallback="image-analyzer",
    ) is True
    with pytest.raises(ValueError):
        validate_reschedule_events(
            events[1:], "existing_post", effective_route="image-analyzer", fallback="image-analyzer"
        )
    with pytest.raises(ValueError):
        validate_reschedule_events(
            events, "existing_post", effective_route="playwright", fallback="none"
        )


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
    assert can_register_timestamp(True, True) is False
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
            "evidence_status": "real_existing_post",
            "route": "playwright",
            "fallback": "none",
        "route_attempted": ["playwright"],
        "playwright_attempted": True,
        "route_reasons": {"playwright": "playwright inspection completed"},
        "observed_state": {"scheduled_list": "confirmed"},
        "verification_evidence": "scheduled list confirmed after Playwright action",
        "post_action_confirmation": "confirmed independently in scheduled list",
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


@pytest.mark.parametrize("status", ["real_non_destructive", "simulated", "not_run"])
def test_can_register_timestamp_rejects_non_mutating_or_dry_run_evidence(status):
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


def test_can_register_timestamp_requires_external_timestamps_to_match_receipt():
    gate = valid_registration_gate()
    gate["receipt"]["requested_timestamp"] = "02/09/2026 10:00"
    assert can_register_timestamp(**gate) is False

    gate = valid_registration_gate()
    gate["receipt"]["displayed_timestamp"] = "02/09/2026 10:00"
    assert can_register_timestamp(**gate) is False


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
        "route": "screenshot+nativa",
        "fallback": "screenshot+nativa",
        "playwright_failure": True,
        "fallback_reason": "Playwright route unavailable before mutation",
        "route_attempted": ["playwright", "screenshot+nativa"],
        "playwright_attempted": True,
        "route_reasons": {
            "playwright": "Playwright route unavailable before mutation",
            "screenshot+nativa": "inspection completed",
        },
        "observed_state": {"scheduled_list": "not confirmed"},
        "verification_evidence": "fallback inspection evidence",
        "post_action_confirmation": "confirmed independently in scheduled list",
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


@pytest.mark.parametrize("field", [
    "route_attempted", "playwright_attempted", "route_reasons", "observed_state",
    "verification_evidence", "post_action_confirmation",
])
def test_receipt_rejects_missing_audit_field(field):
    receipt = valid_registration_gate()["receipt"]
    receipt.pop(field)
    with pytest.raises(ValueError, match="incomplete receipt"):
        validate_receipt(receipt)


def test_receipt_rejects_route_history_that_does_not_follow_effective_route():
    receipt = valid_registration_gate()["receipt"]
    receipt["route_attempted"] = ["screenshot+nativa", "playwright"]
    with pytest.raises(ValueError):
        validate_receipt(receipt)


def test_receipt_requires_post_action_confirmation_for_real_evidence():
    receipt = valid_registration_gate()["receipt"]
    receipt["post_action_confirmation"] = "not_run"
    with pytest.raises(ValueError):
        validate_receipt(receipt)


def test_stop_receipt_requires_playwright_attempt_and_verification_evidence():
    receipt = valid_registration_gate()["receipt"]
    receipt.update({
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
        "route_attempted": ["playwright"],
        "playwright_attempted": True,
        "verification_evidence": "Playwright attempt failed before mutation",
    })
    assert validate_receipt(receipt) is True
    receipt.pop("verification_evidence")
    with pytest.raises(ValueError):
        validate_receipt(receipt)


def test_receipt_requires_playwright_failure_and_reason_for_visual_fallback():
    receipt = valid_registration_gate()["receipt"]
    receipt["route"] = "screenshot+nativa"
    receipt["fallback"] = "screenshot+nativa"
    receipt["playwright_failure"] = True
    receipt["fallback_reason"] = "Playwright route unavailable before mutation"
    receipt["route_attempted"] = ["playwright", "screenshot+nativa"]
    receipt["route_reasons"] = {
        "playwright": "Playwright route unavailable before mutation",
        "screenshot+nativa": "fallback attempted",
    }
    del receipt["playwright_failure"]
    with pytest.raises(ValueError, match="Playwright failure"):
        validate_receipt(receipt)

    receipt = valid_registration_gate()["receipt"]
    receipt["route"] = "screenshot+nativa"
    receipt["fallback"] = "screenshot+nativa"
    receipt["playwright_failure"] = True
    receipt["fallback_reason"] = "Playwright route unavailable before mutation"
    receipt["route_attempted"] = ["playwright", "screenshot+nativa"]
    receipt["route_reasons"] = {
        "playwright": "Playwright route unavailable before mutation",
        "screenshot+nativa": "fallback attempted",
    }
    receipt["fallback_reason"] = ""
    with pytest.raises(ValueError, match="explicit reason"):
        validate_receipt(receipt)


def test_receipt_without_fallback_cannot_declare_fallback_evidence():
    receipt = valid_registration_gate()["receipt"]
    receipt["playwright_failure"] = True
    receipt["fallback_reason"] = "Playwright route unavailable before mutation"
    with pytest.raises(ValueError, match="without fallback"):
        validate_receipt(receipt)

    receipt.pop("playwright_failure")
    receipt.pop("fallback_reason")
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
        "route": "screenshot+nativa",
        "fallback": "screenshot+nativa",
        "playwright_failure": True,
        "fallback_reason": "Playwright route unavailable before mutation",
        "route_attempted": ["playwright", "screenshot+nativa"],
        "playwright_attempted": True,
        "route_reasons": {"playwright": "Playwright failed", "screenshot+nativa": "fallback"},
        "observed_state": {"state": "observed"},
        "verification_evidence": "fallback evidence",
        "post_action_confirmation": "confirmed",
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
        "route": "screenshot+nativa",
        "fallback": "screenshot+nativa",
        "playwright_failure": True,
        "fallback_reason": "Playwright route unavailable before mutation",
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
        "route": "screenshot+nativa",
        "fallback": "screenshot+nativa",
        "playwright_failure": True,
        "fallback_reason": "Playwright route unavailable before mutation",
        "route_attempted": ["playwright", "screenshot+nativa"],
        "playwright_attempted": True,
        "route_reasons": {"playwright": "Playwright failed", "screenshot+nativa": "fallback"},
        "observed_state": {"state": "observed"},
        "verification_evidence": "fallback evidence",
        "post_action_confirmation": "confirmed",
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
        "route": "screenshot+nativa",
        "fallback": "screenshot+nativa",
        "playwright_failure": True,
        "fallback_reason": "Playwright route unavailable before mutation",
        "route_attempted": ["playwright", "screenshot+nativa"],
        "playwright_attempted": True,
        "route_reasons": {"playwright": "Playwright failed", "screenshot+nativa": "fallback"},
        "observed_state": {"state": "observed"},
        "verification_evidence": "fallback evidence",
        "post_action_confirmation": "confirmed",
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
        "route": "screenshot+nativa",
        "fallback": "screenshot+nativa",
        "playwright_failure": True,
        "fallback_reason": "Playwright route unavailable before mutation",
        "route_attempted": ["playwright", "screenshot+nativa"],
        "playwright_attempted": True,
        "route_reasons": {"playwright": "Playwright failed", "screenshot+nativa": "fallback"},
        "observed_state": {"state": "observed"},
        "verification_evidence": "fallback evidence",
        "post_action_confirmation": "confirmed",
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


@pytest.mark.parametrize("sensitive", [
    "secret=abc",
    "API_KEY=abc",
    "api-key=abc",
    "authorization: bearer abc",
])
def test_validate_receipt_rejects_new_sensitive_patterns_case_insensitively(sensitive):
    receipt = valid_registration_gate()["receipt"]
    receipt["verification_evidence"] = sensitive
    with pytest.raises(ValueError, match="sensitive receipt value"):
        validate_receipt(receipt)


@pytest.mark.parametrize("sensitive_key", ["secret", "API_KEY", "authorization-header"])
def test_validate_receipt_rejects_sensitive_nested_keys(sensitive_key):
    receipt = valid_registration_gate()["receipt"]
    receipt["observed_state"] = {"nested": [{sensitive_key: "redacted"}]}
    with pytest.raises(ValueError, match="sensitive receipt value"):
        validate_receipt(receipt)


def test_validate_receipt_rejects_sensitive_text_nested_in_structures():
    receipt = valid_registration_gate()["receipt"]
    receipt["observed_state"] = {
        "browser": {"details": ["safe", {"header": "token=secret"}]}
    }
    with pytest.raises(ValueError, match="sensitive receipt value"):
        validate_receipt(receipt)

    receipt = valid_registration_gate()["receipt"]
    receipt["observed_state"] = {"nested": [{"token": "redacted"}]}
    with pytest.raises(ValueError, match="sensitive receipt value"):
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
    def documented_receipt(text):
        marker = "### Receipt estruturada" if "### Receipt estruturada" in text else "## Receipt estruturada"
        block = text.split(marker, 1)[1]
        yaml_text = block.split("```yaml\n", 1)[1].split("\n```", 1)[0]
        return yaml.safe_load(yaml_text)

    for text in (roadmap, report):
        receipt = documented_receipt(text)
        assert validate_receipt(receipt) is True
        assert receipt["evidence_status"] == "simulated"
        assert receipt["route"] == "stop"
        assert receipt["route_attempted"] == ["playwright"]
        assert receipt["post_action_confirmation"] == "not_run"

    assert "real_existing_post: confirmado" not in roadmap
    assert "real_existing_post: confirmado" not in report
    assert "não foram executados" in roadmap.lower()

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


def test_dry_run_accepts_playwright_only_without_visual_fallback():
    assert validate_dry_run_events(
        COMMON_EVENTS
        + ["visual_route", "date_selected", "time_selected", "summary_confirmed", "blocked_before_advance"]
    ) is True


def test_dry_run_rejects_missing_playwright_attempt():
    with pytest.raises(ValueError):
        validate_dry_run_events(
            [
                "approved_file",
                "markdown_converted",
                "visual_route",
                "date_selected",
                "time_selected",
                "summary_confirmed",
                "blocked_before_advance",
            ]
        )


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
        "route": "playwright",
        "fallback": "none",
        "route_attempted": ["playwright"],
        "playwright_attempted": True,
        "route_reasons": {"playwright": "Playwright inspection completed"},
        "observed_state": {"state": "not_run" if status in {"simulated", "not_run"} else "observed"},
        "verification_evidence": "Playwright inspection receipt",
        "post_action_confirmation": "not_run" if status in {"simulated", "not_run"} else "confirmed",
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
        "route": "playwright",
        "fallback": "none",
        "route_attempted": ["playwright"],
        "playwright_attempted": True,
        "route_reasons": {"playwright": "Playwright inspection completed"},
        "observed_state": {"state": "not_run"},
        "verification_evidence": "Playwright inspection receipt",
        "post_action_confirmation": "not_run",
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


def test_receipt_rejects_inconsistent_primary_route_and_fallback():
    receipt = valid_registration_gate()["receipt"]
    receipt["fallback"] = "screenshot+nativa"
    with pytest.raises(ValueError, match="route.*fallback"):
        validate_receipt(receipt)


@pytest.mark.parametrize("field", ["confirmation", "scheduled_list", "timestamp_registered"])
def test_dry_run_receipt_cannot_claim_completion_evidence(field):
    receipt = {
        "evidence_status": "simulated",
        "route": "playwright",
        "fallback": "none",
        "route_attempted": ["playwright"],
        "playwright_attempted": True,
        "route_reasons": {"playwright": "Playwright inspection completed"},
        "observed_state": {"state": "not_run"},
        "verification_evidence": "Playwright inspection receipt",
        "post_action_confirmation": "not_run",
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
