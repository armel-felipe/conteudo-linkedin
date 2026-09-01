_COMMON = (
    "approved_file",
    "markdown_converted",
    "playwright_attempt",
)

_SUCCESS = (
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

_VISUAL_BRANCHES = {
    "playwright": (),
    "no_native_vision": ("image-analyzer:reason=no_native_vision",),
    "native_failed": (
        "screenshot_fallback_if_needed",
        "image-analyzer:reason=native_failed",
    ),
}


def _validate_exact(events, expected):
    observed = tuple(events)
    if len(observed) != len(set(observed)):
        raise ValueError("duplicate event")
    if observed != expected:
        raise ValueError(f"invalid event sequence: {observed!r}")
    return True


def validate_schedule_events(events, route):
    if route == "unreadable_image":
        expected = _COMMON + (
            "screenshot_fallback_if_needed",
            "image-analyzer:reason=unreadable_image",
            "stop",
        )
    else:
        try:
            branch = _VISUAL_BRANCHES[route]
        except KeyError as error:
            raise ValueError(f"unknown route: {route}") from error
        expected = _COMMON + branch + _SUCCESS
    return _validate_exact(events, expected)


def validate_reschedule_events(events, route):
    if route != "existing_post":
        raise ValueError(f"unknown reschedule route: {route}")
    return _validate_exact(
        events,
        (
            "existing_post_menu",
            "alter_schedule",
            "date_selected",
            "time_selected",
        ),
    )
