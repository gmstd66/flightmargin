import time


def window_metrics(used, reset_at, duration_minutes, now=None):
    if used is None or reset_at is None:
        return None

    now = now or time.time()

    duration_seconds = duration_minutes * 60
    start_at = reset_at - duration_seconds

    elapsed_seconds = max(0, min(duration_seconds, now - start_at))

    elapsed_percent = (
        elapsed_seconds / duration_seconds
    ) * 100

    remaining = max(0, 100 - used)

    if elapsed_percent > 0:
        pace_ratio = used / elapsed_percent
    else:
        pace_ratio = 0

    seconds_until_reset = max(0, reset_at - now)

    if pace_ratio < 0.80:
        pace_status = "SAFE"
    elif pace_ratio <= 1.00:
        pace_status = "ON PACE"
    elif pace_ratio <= 1.25:
        pace_status = "ELEVATED"
    else:
        pace_status = "HIGH"

    exhaustion_at = None

    if used > 0 and elapsed_seconds > 0:
        usage_per_second = used / elapsed_seconds

        if usage_per_second > 0:
            seconds_to_exhaustion = remaining / usage_per_second
            projected = now + seconds_to_exhaustion

            if projected < reset_at:
                exhaustion_at = int(projected)

    return {
        "used": round(used, 2),
        "remaining": round(remaining, 2),
        "reset_at": reset_at,
        "start_at": int(start_at),
        "seconds_until_reset": int(seconds_until_reset),
        "elapsed_percent": round(elapsed_percent, 2),
        "pace_ratio": round(pace_ratio, 2),
        "pace_status": pace_status,
        "projected_exhaustion_at": exhaustion_at,
    }


def enrich_sample(sample):
    if not sample:
        return None

    result = dict(sample)

    result["five_hour"] = window_metrics(
        sample.get("five_hour_used"),
        sample.get("five_hour_reset_at"),
        300,
    )

    result["weekly"] = window_metrics(
        sample.get("weekly_used"),
        sample.get("weekly_reset_at"),
        10080,
    )

    return result
