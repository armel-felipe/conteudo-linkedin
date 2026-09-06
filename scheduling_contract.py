import re

from execution_log import ExecutionLogger


_COMMON = (
    "approved_file",
    "markdown_converted",
    "mcp_chrome_devtools_attempt",
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
    "playwright": ("playwright_fallback", "playwright_attempt"),
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
    "route_attempted",
    "mcp_attempted",
    "route_reasons",
    "observed_state",
    "verification_evidence",
    "post_action_confirmation",
)
_RECEIPT_FALLBACK_FIELDS = {
    "mcp_failure",
    "fallback_reason",
}

_RECEIPT_ROUTES = {"mcp_chrome_devtools", "playwright_fallback", "stop"}
_RECEIPT_FALLBACKS = {"none", "playwright_fallback"}
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
_FORBIDDEN_RECEIPT_PATTERN = re.compile(
    r"secret|api[\s_-]*key|authorization",
    re.IGNORECASE,
)


def _validate_exact(events, expected):
    observed = tuple(events)
    if len(observed) != len(set(observed)):
        raise ValueError("duplicate event")
    if observed != expected:
        raise ValueError(f"invalid event sequence: {observed!r}")
    return True


def validate_schedule_events(events, route):
    observed = tuple(events)
    playwright_indexes = [
        index for index, event in enumerate(observed) if "playwright" in event
    ]
    if playwright_indexes:
        mcp_index = next(
            (
                index
                for index, event in enumerate(observed)
                if event == "mcp_chrome_devtools_attempt"
            ),
            None,
        )
        if mcp_index is None or mcp_index > min(playwright_indexes):
            raise ValueError(
                "MCP Chrome DevTools must be attempted before Playwright"
            )
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


def validate_reschedule_events(events, route, *, effective_route=None, fallback=None):
    if route != "existing_post":
        raise ValueError(f"unknown reschedule route: {route}")
    observed = tuple(events)
    if not observed or observed[0] != "mcp_chrome_devtools_attempt":
        raise ValueError("reschedule requires an MCP Chrome DevTools attempt")
    if effective_route not in _RECEIPT_ROUTES - {"stop"}:
        raise ValueError("reschedule requires an effective browser route")
    if effective_route == "playwright_fallback":
        if fallback != "playwright_fallback":
            raise ValueError("Playwright reschedule requires a valid fallback")
        if "playwright_fallback" not in observed or "playwright_attempt" not in observed:
            raise ValueError("Playwright reschedule requires fallback evidence")
    elif fallback != "none":
        raise ValueError("MCP reschedule requires fallback none")
    if effective_route == "mcp_chrome_devtools" and "playwright_fallback" in observed:
        raise ValueError("effective route cannot be MCP after Playwright fallback")
    return _validate_exact(
        events,
        (
            "mcp_chrome_devtools_attempt",
            *(("playwright_fallback", "playwright_attempt") if effective_route == "playwright_fallback" else ()),
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


def can_register_timestamp(
    confirmation,
    scheduled_list,
    *,
    receipt=None,
    summary=None,
    requested_timestamp=None,
    displayed_timestamp=None,
    timestamp_registered=None,
    failure_state=None,
):
    """Allow timestamp registration only after every explicit gate passes."""
    if type(confirmation) is not bool or confirmation is not True:
        return False
    if type(scheduled_list) is not bool or scheduled_list is not True:
        return False

    if not isinstance(receipt, dict):
        return False
    try:
        if not validate_receipt(receipt):
            return False
    except (TypeError, ValueError):
        return False
    if receipt["evidence_status"] != "real_existing_post":
        return False
    if receipt.get("mcp_attempted") is not True:
        return False
    if not isinstance(receipt.get("route_attempted"), list) or not receipt["route_attempted"]:
        return False
    if not isinstance(receipt.get("verification_evidence"), str) or not receipt["verification_evidence"].strip():
        return False
    if summary != "pass":
        return False
    if type(timestamp_registered) is not bool or timestamp_registered is not True:
        return False
    if type(requested_timestamp) is not str or not requested_timestamp:
        return False
    if type(displayed_timestamp) is not str or not displayed_timestamp:
        return False
    if requested_timestamp != displayed_timestamp:
        return False
    if requested_timestamp != receipt["requested_timestamp"]:
        return False
    if displayed_timestamp != receipt["displayed_timestamp"]:
        return False
    if not all(receipt[field] == "pass" for field in ("preview", "confirmation", "scheduled_list", "timestamp_registered")):
        return False
    if failure_state is not None:
        return False
    return True


def validate_dry_run_events(events):
    observed = tuple(events)
    playwright_indexes = [
        index for index, event in enumerate(observed) if "playwright" in event
    ]
    mcp_index = next(
        (
            index
            for index, event in enumerate(observed)
            if event == "mcp_chrome_devtools_attempt"
        ),
        None,
    )
    if playwright_indexes and (mcp_index is None or mcp_index > min(playwright_indexes)):
        raise ValueError("MCP Chrome DevTools must be attempted before Playwright")
    base = (
        "approved_file",
        "markdown_converted",
        "mcp_chrome_devtools_attempt",
    )
    suffix = (
        "visual_route",
        "date_selected",
        "time_selected",
        "summary_confirmed",
        "blocked_before_advance",
    )
    if playwright_indexes:
        if "playwright_fallback" not in observed:
            raise ValueError("playwright_fallback required before playwright_attempt")
        return _validate_exact(
            events, base + ("playwright_fallback", "playwright_attempt") + suffix
        )
    return _validate_exact(events, base + suffix)


def validate_receipt(receipt):
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be an object")
    fields = set(receipt)
    if not set(_RECEIPT_FIELDS).issubset(fields) or not fields <= (
        set(_RECEIPT_FIELDS) | _RECEIPT_FALLBACK_FIELDS
    ):
        raise ValueError("incomplete receipt")
    if receipt["evidence_status"] not in _EVIDENCE_STATUSES:
        raise ValueError("invalid evidence status")
    if receipt["route"] not in _RECEIPT_ROUTES:
        raise ValueError("invalid receipt route")
    if receipt["fallback"] not in _RECEIPT_FALLBACKS:
        raise ValueError("invalid receipt fallback")
    if receipt["mcp_attempted"] is not True:
        raise ValueError("receipt requires MCP attempt evidence")
    attempted = receipt["route_attempted"]
    if (
        not isinstance(attempted, list)
        or not attempted
        or any(route not in _RECEIPT_ROUTES - {"stop"} for route in attempted)
        or len(attempted) != len(set(attempted))
        or attempted[0] != "mcp_chrome_devtools"
    ):
        raise ValueError("invalid attempted route order")
    if receipt["route"] == "mcp_chrome_devtools" and attempted != ["mcp_chrome_devtools"]:
        raise ValueError("effective route does not match attempted route order")
    if receipt["route"] == "playwright_fallback" and attempted != [
        "mcp_chrome_devtools", "playwright_fallback"
    ]:
        raise ValueError("effective route does not match attempted route order")
    if receipt["route"] == "stop" and attempted not in (
        ["mcp_chrome_devtools"],
        ["mcp_chrome_devtools", "playwright_fallback"],
    ):
        raise ValueError("stop route has invalid attempted route order")
    reasons = receipt["route_reasons"]
    if (
        not isinstance(reasons, dict)
        or set(reasons) != set(attempted)
        or any(not isinstance(reason, str) or not reason.strip() for reason in reasons.values())
    ):
        raise ValueError("receipt requires reasons for every attempted route")
    observed_state = receipt["observed_state"]
    if observed_state is None or observed_state == "" or observed_state == {}:
        raise ValueError("receipt requires observed state")
    if not isinstance(receipt["verification_evidence"], str) or not receipt["verification_evidence"].strip():
        raise ValueError("receipt requires verification evidence")
    if not isinstance(receipt["post_action_confirmation"], str) or not receipt[
        "post_action_confirmation"
    ].strip():
        raise ValueError("receipt requires post-action confirmation")
    if receipt["route"] == "stop":
        if receipt["fallback"] != "none":
            raise ValueError("stop receipt cannot declare a fallback")
        if receipt.get("mcp_attempted") is not True:
            raise ValueError("stop receipt requires MCP attempt evidence")
        if not isinstance(receipt.get("route_attempted"), list) or "mcp_chrome_devtools" not in receipt["route_attempted"]:
            raise ValueError("stop receipt requires attempted route evidence")
        if not isinstance(receipt.get("verification_evidence"), str) or not receipt["verification_evidence"].strip():
            raise ValueError("stop receipt requires verification evidence")
    elif receipt["route"] == "mcp_chrome_devtools":
        if receipt["fallback"] != "none":
            raise ValueError("receipt route and fallback are inconsistent")
        if "mcp_failure" in fields or "fallback_reason" in fields:
            raise ValueError("receipt declares fallback evidence without fallback")
    elif receipt["fallback"] != "playwright_fallback":
        raise ValueError("receipt route and fallback are inconsistent")
    if receipt["route"] == "playwright_fallback":
        if receipt.get("mcp_failure") is not True:
            raise ValueError("playwright fallback requires MCP failure")
        if not isinstance(receipt.get("fallback_reason"), str) or not receipt[
            "fallback_reason"
        ].strip():
            raise ValueError("playwright fallback requires an explicit reason")
    status = receipt["evidence_status"]
    if status in {"real_non_destructive", "real_existing_post"}:
        if receipt["requested_timestamp"] != receipt["displayed_timestamp"]:
            raise ValueError("receipt timestamp mismatch")
        if not all(receipt[field] == "pass" for field in ("date_selected", "time_selected", "summary")):
            raise ValueError("receipt gate failed")
        if any(receipt[field] not in {"not_run", "pass"} for field in ("preview", "confirmation", "scheduled_list", "timestamp_registered")):
            raise ValueError("receipt claims unexecuted completion")
        if receipt["post_action_confirmation"] == "not_run":
            raise ValueError("real receipt requires post-action confirmation")
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
    def contains_sensitive_value(value):
        if isinstance(value, str):
            return (
                any(term in value.lower() for term in _FORBIDDEN_RECEIPT_TERMS)
                or _FORBIDDEN_RECEIPT_PATTERN.search(value) is not None
            )
        if isinstance(value, dict):
            return any(
                contains_sensitive_value(key) or contains_sensitive_value(item)
                for key, item in value.items()
            )
        if isinstance(value, (list, tuple, set)):
            return any(contains_sensitive_value(item) for item in value)
        return False

    if contains_sensitive_value(receipt):
        raise ValueError("sensitive receipt value")
    return True


def validate_receipt_with_log(
    receipt,
    logger: ExecutionLogger,
    *,
    receipt_ref=None,
):
    """Validate a receipt and record only the sanitized validation outcome."""

    try:
        valid = validate_receipt(receipt)
    except Exception as error:
        logger.finish(
            "scheduling",
            "blocked",
            state="receipt_invalid",
            receipt_ref=receipt_ref,
            reason=type(error).__name__,
        )
        raise
    logger.finish(
        "scheduling",
        "completed",
        state="confirmed",
        receipt_ref=receipt_ref,
        effective_route=receipt.get("route"),
        route_attempted=receipt.get("route_attempted", ()),
        reason="receipt_validated",
    )
    return valid
