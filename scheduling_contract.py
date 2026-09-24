import re

from execution_log import ExecutionLogger


_COMMON = (
    "approved_file",
    "markdown_converted",
    "browser_attempt",
    "screenshot",
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

# Browser routes are the only routes in the chain. Vision is orthogonal and is
# validated through the receipt `vision` field, never as a browser route.
_BROWSER_BRANCHES = {
    "browser_native": (),
    "playwright_mcp": ("playwright_mcp_attempt",),
    "playwright": ("playwright_attempt",),
}

_RECEIPT_FIELDS = (
    "evidence_status",
    "route",
    "fallback",
    "vision",
    "vision_fallback_reason",
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
    "browser_attempted",
    "route_reasons",
    "observed_state",
    "verification_evidence",
    "post_action_confirmation",
)
_RECEIPT_FALLBACK_FIELDS = {
    "image_analyzer_failure",
    "playwright_attempted",
    "playwright_mcp_attempted",
    "playwright_failure",
    "fallback_reason",
}

_RECEIPT_ROUTES = {"browser_native", "playwright_mcp", "playwright", "stop"}
_RECEIPT_FALLBACKS = {"none", "browser_native", "playwright_mcp", "playwright"}
_VISION_MODES = {"native", "image-analyzer"}
_VISION_FALLBACK_REASONS = {"no_native_vision", "native_failed"}
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
    if route == "unreadable_image":
        expected = _COMMON + (
            "image-analyzer:reason=unreadable_image",
            "stop",
        )
    else:
        try:
            branch = _BROWSER_BRANCHES[route]
        except KeyError as error:
            raise ValueError(f"unknown route: {route}") from error
        expected = _COMMON + ("visual_route",) + branch + _SUCCESS[1:]
    return _validate_exact(events, expected)


def validate_reschedule_events(
    events, route, *, effective_route=None, fallback=None, vision=None
):
    if route != "existing_post":
        raise ValueError(f"unknown reschedule route: {route}")
    observed = tuple(events)
    if not observed or observed[0] != "browser_attempt":
        raise ValueError("reschedule requires a browser attempt")
    if effective_route not in _RECEIPT_ROUTES - {"stop"}:
        raise ValueError("reschedule requires an effective browser route")
    if effective_route == "browser_native":
        if fallback != "none":
            raise ValueError("visual reschedule requires no fallback")
    elif effective_route == "playwright_mcp":
        if fallback != "playwright_mcp":
            raise ValueError("playwright_mcp reschedule requires fallback evidence")
        if "playwright_mcp_attempt" not in observed:
            raise ValueError("playwright_mcp reschedule requires attempt evidence")
    elif effective_route == "playwright":
        if fallback != "playwright":
            raise ValueError("Playwright reschedule requires fallback evidence")
        if "playwright_attempt" not in observed:
            raise ValueError("Playwright reschedule requires attempt evidence")
    if vision is not None and vision not in _VISION_MODES:
        raise ValueError("reschedule requires a valid vision mode")
    return _validate_exact(
        observed,
        (
            "browser_attempt",
            *(("playwright_mcp_attempt",) if effective_route == "playwright_mcp" else ()),
            *(("playwright_attempt",) if effective_route == "playwright" else ()),
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
    if receipt.get("browser_attempted") is not True:
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
    base = _COMMON
    suffix = (
        "visual_route",
        "date_selected",
        "time_selected",
        "summary_confirmed",
        "blocked_before_advance",
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
    if receipt["vision"] not in _VISION_MODES:
        raise ValueError("invalid receipt vision")
    vision_reason = receipt["vision_fallback_reason"]
    if receipt["vision"] == "native":
        if vision_reason is not None:
            raise ValueError("native vision cannot declare a fallback reason")
    else:
        if vision_reason not in _VISION_FALLBACK_REASONS:
            raise ValueError("image-analyzer vision requires a fallback reason")
        if vision_reason == "native_failed" and receipt.get("image_analyzer_failure") is not True:
            raise ValueError("image-analyzer vision requires native failure evidence")
    if receipt.get("browser_attempted") is not True:
        raise ValueError("receipt requires browser attempt evidence")
    attempted = receipt["route_attempted"]
    expected_orders = {
        "browser_native": [["browser_native"]],
        "playwright_mcp": [["browser_native", "playwright_mcp"]],
        "playwright": [
            ["browser_native", "playwright_mcp", "playwright"],
            ["browser_native", "playwright"],
        ],
        "stop": [
            ["browser_native"],
            ["browser_native", "playwright_mcp"],
            ["browser_native", "playwright"],
            ["browser_native", "playwright_mcp", "playwright"],
        ],
    }
    if (
        not isinstance(attempted, list)
        or not attempted
        or any(route not in _RECEIPT_ROUTES - {"stop"} for route in attempted)
        or len(attempted) != len(set(attempted))
        or attempted not in expected_orders.get(receipt["route"], [])
    ):
        raise ValueError("invalid attempted route order")
    if receipt["route"] == "browser_native":
        if receipt["fallback"] != "none":
            raise ValueError("browser_native route requires no fallback")
    if receipt["route"] == "playwright_mcp":
        if receipt.get("playwright_mcp_attempted") is not True:
            raise ValueError("playwright_mcp route requires attempt evidence")
        if receipt["fallback"] != "playwright_mcp":
            raise ValueError("receipt route and fallback are inconsistent")
    if receipt["route"] == "playwright":
        if receipt.get("playwright_attempted") is not True:
            raise ValueError("Playwright route requires attempt evidence")
        if receipt["fallback"] != "playwright":
            raise ValueError("receipt route and fallback are inconsistent")
        if "playwright_failure" in fields:
            raise ValueError("receipt declares fallback evidence without fallback")
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
        if not isinstance(receipt.get("verification_evidence"), str) or not receipt["verification_evidence"].strip():
            raise ValueError("stop receipt requires verification evidence")
    status = receipt["evidence_status"]
    if status in {"real_non_destructive", "real_existing_post"}:
        if receipt["requested_timestamp"] != receipt["displayed_timestamp"]:
            raise ValueError("receipt timestamp mismatch")
        if not all(receipt[field] == "pass" for field in ("date_selected", "time_selected", "summary")):
            raise ValueError("receipt gate failed")
        if any(receipt[field] not in {"not_run", "pass", True} for field in ("preview", "confirmation", "scheduled_list", "timestamp_registered")):
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
