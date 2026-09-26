import asyncio
import time
from pathlib import Path

import pytest
from fastapi import HTTPException

import app.main as main_module
from app.adapters.codex_stdio import CodexAppServer, CodexNotFoundError
from app.storage.sqlite_store import SQLiteQuotaStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_TEMPLATE = PROJECT_ROOT / "app" / "templates" / "index.html"
SETTINGS_TEMPLATE = PROJECT_ROOT / "app" / "templates" / "settings.html"
DASHBOARD_SCRIPT = PROJECT_ROOT / "app" / "static" / "app.js"
SETTINGS_SCRIPT = PROJECT_ROOT / "app" / "static" / "settings.js"


def test_collector_loop_waits_before_next_sample(monkeypatch):
    collections = []
    sleeps = []

    async def collect():
        collections.append(True)

    async def sleep(seconds):
        sleeps.append(seconds)
        raise asyncio.CancelledError

    monkeypatch.setattr(main_module, "collect", collect)
    monkeypatch.setattr(main_module.asyncio, "sleep", sleep)

    asyncio.run(main_module.collector_loop())

    assert sleeps == [main_module.SAMPLE_INTERVAL]
    assert collections == []


def sample(*, credits="365.8930500000"):
    now = int(time.time())
    return {
        "id": 1,
        "captured_at": now,
        "five_hour_used": 90,
        "five_hour_reset_at": now + 3600,
        "weekly_used": 75,
        "weekly_reset_at": now + 86400,
        "plan_type": "plus",
        "reset_credits_available": 2,
        "credits_balance": credits,
        "spend_control_reached": 0,
        "rate_limit_reached_type": None,
    }


def test_shared_quota_api_contract_is_additive_and_contains_semantic_states(monkeypatch):
    monkeypatch.setattr(main_module.store, "get_latest_sample", lambda: sample())

    result = asyncio.run(main_module.quota())

    assert result["five_hour"]["remaining"] == 10
    assert result["five_hour"]["state"] == "critical"
    assert result["weekly"]["remaining"] == 25
    assert result["weekly"]["state"] == "warning"
    assert result["credits_balance"] == "365.8930500000"
    assert result["plan_type"] == "plus"
    assert result["reset_credits_available"] == 2
    assert result["collector"] is main_module.collector_status


def test_history_contract_preserves_shared_sample_fields(monkeypatch):
    stored = sample(credits=None)
    monkeypatch.setattr(main_module.store, "get_history", lambda hours: [stored])

    result = asyncio.run(main_module.history(hours=168))

    assert result == {"hours": 168, "samples": [stored]}
    assert result["samples"][0]["credits_balance"] is None
    assert result["samples"][0]["weekly_reset_at"] is not None


def test_sqlite_history_keeps_quota_account_reset_and_credit_fields(tmp_path, monkeypatch):
    store = SQLiteQuotaStore(tmp_path / "quota.db")
    store.initialize()
    monkeypatch.setattr("app.storage.sqlite_store.time.time", lambda: 2_000_000_000)

    inserted = store.insert_sample(sample())
    history = store.get_history(hours=168)

    assert history == [inserted]
    assert history[0]["credits_balance"] == "365.8930500000"
    assert history[0]["reset_credits_available"] == 2
    assert history[0]["plan_type"] == "plus"


def test_dashboard_order_and_browser_settings_match_platform_parity():
    dashboard = DASHBOARD_TEMPLATE.read_text(encoding="utf-8")
    settings = SETTINGS_TEMPLATE.read_text(encoding="utf-8")
    dashboard_script = DASHBOARD_SCRIPT.read_text(encoding="utf-8")
    settings_script = SETTINGS_SCRIPT.read_text(encoding="utf-8")

    panel_positions = [
        dashboard.index(f'data-panel="{panel_id}"')
        for panel_id in ("five-hour", "weekly", "pace", "resets", "account", "history")
    ]
    assert panel_positions == sorted(panel_positions)
    assert 'window.location.assign("/settings")' in dashboard_script
    assert dashboard_script.count('data.state === "') == 2
    assert "QUOTA_THRESHOLDS" not in dashboard_script
    assert "function formatCredits(value)" in dashboard_script
    assert "Credits: unavailable" in dashboard_script
    assert "Credits: 0 (depleted)" in dashboard_script
    assert settings.count("data-native-only") == 4
    assert '["dashboard", "about"]' in settings_script
    assert 'window.location.assign("/")' in settings_script


def test_collector_uses_canonical_structured_rate_limit_method(monkeypatch):
    client = CodexAppServer(executable="codex")
    observed = []
    monkeypatch.setattr(client, "request", lambda method: observed.append(method) or {})

    assert client.get_rate_limits() == {}
    assert observed == ["account/rateLimits/read"]


def test_collector_errors_have_safe_shared_user_messages():
    assert main_module.collector_message(CodexNotFoundError("private path")) == (
        "Codex CLI was not found. Install Codex or set CODEX_BIN."
    )
    assert main_module.collector_message(RuntimeError("authentication required")) == (
        "Codex authentication is unavailable. Authenticate with Codex and retry."
    )
    generic = main_module.collector_message(RuntimeError("sensitive internal failure"))
    assert generic == (
        "Quota collection temporarily failed. Check About diagnostics and application logs."
    )
    assert "sensitive" not in generic


def test_quota_unavailable_response_uses_public_collector_message(monkeypatch):
    monkeypatch.setattr(main_module.store, "get_latest_sample", lambda: None)
    monkeypatch.setitem(main_module.collector_status, "last_error", "private internal detail")
    monkeypatch.setitem(main_module.collector_status, "message", "Codex CLI was not found.")

    with pytest.raises(HTTPException) as raised:
        asyncio.run(main_module.quota())

    assert raised.value.status_code == 503
    assert raised.value.detail == "Codex CLI was not found."
