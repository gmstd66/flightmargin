from app.main import normalize


def sample_response():
    return {
        "limits": {
            "limitId": "codex",
            "primary": {
                "usedPercent": 42,
                "windowDurationMins": 300,
                "resetsAt": 1788999919,
            },
            "secondary": {
                "usedPercent": 25,
                "windowDurationMins": 10080,
                "resetsAt": 1789494339,
            },
            "credits": {
                "hasCredits": False,
                "unlimited": False,
                "balance": "0",
            },
            "spendControlReached": False,
            "planType": "plus",
            "rateLimitReachedType": None,
        },
        "reset_credits": {
            "availableCount": 3,
            "credits": [],
        },
    }


def test_normalize_identifies_five_hour_window():
    result = normalize(sample_response())

    assert result["five_hour_used"] == 42
    assert result["five_hour_reset_at"] == 1788999919


def test_normalize_identifies_weekly_window():
    result = normalize(sample_response())

    assert result["weekly_used"] == 25
    assert result["weekly_reset_at"] == 1789494339


def test_normalize_account_metadata():
    result = normalize(sample_response())

    assert result["plan_type"] == "plus"
    assert result["reset_credits_available"] == 3
    assert result["credits_balance"] == "0"
    assert result["spend_control_reached"] is False
    assert result["rate_limit_reached_type"] is None


def test_normalize_does_not_depend_on_primary_secondary_order():
    raw = sample_response()

    raw["limits"]["primary"], raw["limits"]["secondary"] = (
        raw["limits"]["secondary"],
        raw["limits"]["primary"],
    )

    result = normalize(raw)

    assert result["five_hour_used"] == 42
    assert result["weekly_used"] == 25


def test_normalize_handles_missing_five_hour_window():
    raw = sample_response()
    raw["limits"]["primary"] = None

    result = normalize(raw)

    assert result["five_hour_used"] is None
    assert result["five_hour_reset_at"] is None
    assert result["weekly_used"] == 25


def test_normalize_handles_missing_reset_credits():
    raw = sample_response()
    raw["reset_credits"] = {}

    result = normalize(raw)

    assert result["reset_credits_available"] == 0
