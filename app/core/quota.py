from typing import Any


FIVE_HOUR_MINUTES = 300
WEEKLY_MINUTES = 10080


def _find_window(
    snapshot: dict[str, Any],
    duration_minutes: int,
):
    for key in ("primary", "secondary"):
        window = snapshot.get(key)

        if not window:
            continue

        if window.get("windowDurationMins") == duration_minutes:
            return window

    return None


def _extract_snapshot(response: dict[str, Any]):
    """
    Accept either:

    1. The native account/rateLimits/read response, or
    2. The original prototype wrapper:
       {"limits": ..., "reset_credits": ...}

    Supporting both makes the migration backward-compatible.
    """

    if "limits" in response:
        snapshot = response.get("limits")

        if not snapshot:
            raise RuntimeError(
                "Codex rate-limit data missing from response"
            )

        reset_credits = response.get("reset_credits") or {}

        return snapshot, reset_credits

    limits_by_id = (
        response.get("rateLimitsByLimitId")
        or {}
    )

    if "codex" in limits_by_id:
        snapshot = limits_by_id["codex"]

    else:
        snapshot = response.get("rateLimits")

    if not snapshot:
        raise RuntimeError(
            "Codex rate-limit data missing from response"
        )

    reset_credits = (
        response.get("rateLimitResetCredits")
        or {}
    )

    return snapshot, reset_credits


def normalize_rate_limits(
    response: dict[str, Any],
):
    snapshot, reset_credits = (
        _extract_snapshot(response)
    )

    five_hour = _find_window(
        snapshot,
        FIVE_HOUR_MINUTES,
    )

    weekly = _find_window(
        snapshot,
        WEEKLY_MINUTES,
    )

    credits = (
        snapshot.get("credits")
        or {}
    )

    return {
        "five_hour_used": (
            five_hour.get("usedPercent")
            if five_hour
            else None
        ),

        "five_hour_reset_at": (
            five_hour.get("resetsAt")
            if five_hour
            else None
        ),

        "weekly_used": (
            weekly.get("usedPercent")
            if weekly
            else None
        ),

        "weekly_reset_at": (
            weekly.get("resetsAt")
            if weekly
            else None
        ),

        "plan_type":
            snapshot.get("planType"),

        "reset_credits_available":
            reset_credits.get(
                "availableCount",
                0,
            ),

        "credits_balance":
            credits.get("balance"),

        "spend_control_reached":
            snapshot.get(
                "spendControlReached",
                False,
            ),

        "rate_limit_reached_type":
            snapshot.get(
                "rateLimitReachedType"
            ),
    }
