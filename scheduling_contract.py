SCHEDULE_EVENTS = (
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


def expected_schedule_events():
    return SCHEDULE_EVENTS


def reschedule_events():
    return (
        "existing_post_menu",
        "alter_schedule",
        "date_selected",
        "time_selected",
    )


def visual_route(branch):
    routes = {
        "playwright": ("playwright_attempt", "visual_route"),
        "no_native_vision": (
            "playwright_attempt",
            "image-analyzer:reason=no_native_vision",
            "visual_route",
        ),
        "native_failed": (
            "playwright_attempt",
            "screenshot_fallback_if_needed",
            "image-analyzer:reason=native_failed",
            "visual_route",
        ),
        "unreadable_image": (
            "playwright_attempt",
            "screenshot_fallback_if_needed",
            "image-analyzer:reason=unreadable_image",
            "stop",
        ),
    }
    return routes[branch]
