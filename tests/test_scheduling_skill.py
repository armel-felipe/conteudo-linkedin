from scheduling_contract import expected_schedule_events, reschedule_events, visual_route


EXPECTED_EVENTS = (
    "approved_file",
    "markdown_converted",
    "playwright_attempt",
    "screenshot_fallback_if_needed",
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
)


def test_scheduling_contract_emits_expected_event_sequence():
    assert expected_schedule_events() == EXPECTED_EVENTS


def test_rescheduling_uses_existing_post_and_never_a_new_composer():
    assert reschedule_events() == (
        "existing_post_menu",
        "alter_schedule",
        "date_selected",
        "time_selected",
    )
    assert "new_composer" not in reschedule_events()


def test_visual_routes_cover_branches_and_stop_on_unreadable_image():
    assert visual_route("playwright") == ("playwright_attempt", "visual_route")
    assert visual_route("no_native_vision") == (
        "playwright_attempt",
        "image-analyzer:reason=no_native_vision",
        "visual_route",
    )
    assert visual_route("native_failed") == (
        "playwright_attempt",
        "screenshot_fallback_if_needed",
        "image-analyzer:reason=native_failed",
        "visual_route",
    )
    assert visual_route("unreadable_image") == (
        "playwright_attempt",
        "screenshot_fallback_if_needed",
        "image-analyzer:reason=unreadable_image",
        "stop",
    )
