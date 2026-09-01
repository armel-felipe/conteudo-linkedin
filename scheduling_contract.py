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

_RECEIPT_FIELDS = (
    "evidence_status",
    "route",
    "fallback",
    "requested_timestamp",
    "displayed_timestamp",
    "date_selected",
    "time_selected",
    "summary",
    "preview",
    "confirmation",
    "scheduled_list",
    "timestamp_registered",
    "duplicate_created",
)

_RECEIPT_ROUTES = {"playwright", "browser_cdp"}
_RECEIPT_FALLBACKS = {"none", "native", "no_native_vision", "native_failed"}
_EVIDENCE_STATUSES = {
    "real_non_destructive",
    "real_existing_post",
    "simulated",
    "not_run",
}
_FORBIDDEN_RECEIPT_TERMS = (
    "cookie",
    "cookies",
    "token",
    "senha",
    "password",
    "email",
    "account_id",
    "account id",
    "identificador",
    "identificadores",
)


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
            "summary_confirmed",
            "advance",
            "final_preview_confirmed",
            "schedule",
            "confirmation",
            "scheduled_list_confirmed",
            "timestamp_registered",
        ),
    )


def can_advance_schedule(requested_timestamp, displayed_timestamp):
    return requested_timestamp == displayed_timestamp


def can_register_timestamp(confirmation, scheduled_list):
    return bool(confirmation and scheduled_list)


def validate_dry_run_events(events):
    return _validate_exact(
        events,
        (
            "approved_file",
            "markdown_converted",
            "playwright_attempt",
            "visual_route",
            "date_selected",
            "time_selected",
            "summary_confirmed",
            "blocked_before_advance",
        ),
    )


def validate_receipt(receipt):
    if set(receipt) != set(_RECEIPT_FIELDS):
        raise ValueError("incomplete receipt")
    if receipt["evidence_status"] not in _EVIDENCE_STATUSES:
        raise ValueError("invalid evidence status")
    if receipt["route"] not in _RECEIPT_ROUTES:
        raise ValueError("invalid receipt route")
    if receipt["fallback"] not in _RECEIPT_FALLBACKS:
        raise ValueError("invalid receipt fallback")
    status = receipt["evidence_status"]
    if status in {"real_non_destructive", "real_existing_post"}:
        if receipt["requested_timestamp"] != receipt["displayed_timestamp"]:
            raise ValueError("receipt timestamp mismatch")
        if not all(receipt[field] == "pass" for field in ("date_selected", "time_selected", "summary")):
            raise ValueError("receipt gate failed")
        if any(receipt[field] != "not_run" for field in ("preview", "confirmation", "scheduled_list", "timestamp_registered")):
            raise ValueError("receipt claims unexecuted completion")
    else:
        if receipt["requested_timestamp"] or receipt["displayed_timestamp"]:
            raise ValueError("non-real receipt timestamp")
        if any(
            receipt[field] != "not_run"
            for field in (
                "date_selected",
                "time_selected",
                "summary",
                "preview",
                "confirmation",
                "scheduled_list",
                "timestamp_registered",
            )
        ):
            raise ValueError("receipt gate failed")
    if receipt["duplicate_created"] is not False:
        raise ValueError("duplicate publication recorded")
    if status in {"real_non_destructive", "real_existing_post"} and (
        not receipt["requested_timestamp"] or not receipt["displayed_timestamp"]
    ):
        raise ValueError("receipt timestamp missing")
    for value in receipt.values():
        if isinstance(value, str) and any(term in value.lower() for term in _FORBIDDEN_RECEIPT_TERMS):
            raise ValueError("sensitive receipt value")
    return True
