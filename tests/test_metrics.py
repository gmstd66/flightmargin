from app.core.metrics import window_metrics, enrich_sample


def make_window(
    *,
    used,
    elapsed_percent,
    duration_minutes=10080,
):
    duration_seconds = duration_minutes * 60

    now = 2_000_000_000

    elapsed_seconds = (
        duration_seconds
        * elapsed_percent
        / 100
    )

    start_at = now - elapsed_seconds
    reset_at = start_at + duration_seconds

    return window_metrics(
        used=used,
        reset_at=reset_at,
        duration_minutes=duration_minutes,
        now=now,
    )


def test_remaining_percentage():
    result = make_window(
        used=26,
        elapsed_percent=50,
    )

    assert result["used"] == 26
    assert result["remaining"] == 74


def test_safe_pace():
    result = make_window(
        used=30,
        elapsed_percent=50,
    )

    assert result["pace_ratio"] == 0.6
    assert result["pace_status"] == "SAFE"


def test_on_pace_lower_boundary():
    result = make_window(
        used=40,
        elapsed_percent=50,
    )

    assert result["pace_ratio"] == 0.8
    assert result["pace_status"] == "ON PACE"


def test_on_pace_upper_boundary():
    result = make_window(
        used=50,
        elapsed_percent=50,
    )

    assert result["pace_ratio"] == 1.0
    assert result["pace_status"] == "ON PACE"


def test_elevated_pace():
    result = make_window(
        used=55,
        elapsed_percent=50,
    )

    assert result["pace_ratio"] == 1.1
    assert result["pace_status"] == "ELEVATED"


def test_high_pace():
    result = make_window(
        used=75,
        elapsed_percent=50,
    )

    assert result["pace_ratio"] == 1.5
    assert result["pace_status"] == "HIGH"


def test_projected_exhaustion_when_usage_is_too_fast():
    result = make_window(
        used=75,
        elapsed_percent=50,
    )

    assert result["projected_exhaustion_at"] is not None
    assert (
        result["projected_exhaustion_at"]
        < result["reset_at"]
    )


def test_no_projected_exhaustion_when_quota_lasts_to_reset():
    result = make_window(
        used=25,
        elapsed_percent=50,
    )

    assert result["projected_exhaustion_at"] is None


def test_seconds_until_reset():
    duration_minutes = 300
    duration_seconds = duration_minutes * 60

    now = 2_000_000_000
    elapsed_seconds = 60 * 60

    reset_at = (
        now
        - elapsed_seconds
        + duration_seconds
    )

    result = window_metrics(
        used=20,
        reset_at=reset_at,
        duration_minutes=duration_minutes,
        now=now,
    )

    assert result["seconds_until_reset"] == 4 * 60 * 60


def test_missing_window_returns_none():
    assert (
        window_metrics(
            used=None,
            reset_at=None,
            duration_minutes=300,
        )
        is None
    )


def test_enrich_sample_creates_both_windows():
    sample = {
        "five_hour_used": 20,
        "five_hour_reset_at": 2_000_018_000,
        "weekly_used": 35,
        "weekly_reset_at": 2_000_604_800,
    }

    result = enrich_sample(sample)

    assert result["five_hour"] is not None
    assert result["weekly"] is not None

    assert result["five_hour"]["remaining"] == 80
    assert result["weekly"]["remaining"] == 65
