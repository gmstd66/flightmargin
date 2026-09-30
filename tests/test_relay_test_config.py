from __future__ import annotations

import pytest

from tests.relay_test_config import (
    RUNTIME_DATABASE_URL_ENV,
    RUNTIME_PEPPER_ENV,
    TEST_DATABASE_URL_ENV,
    TEST_PEPPER_ENV,
    UNAVAILABLE_REASON,
    relay_test_config_or_skip,
    resolve_relay_test_config,
)
from tests import test_mobile_relay_schema


LOCAL_URL = "postgresql://relay:local-password@127.0.0.1:55432/postgres"
LOCAL_PEPPER = "local-test-pepper-value-at-least-32-bytes"
REMOTE_URL = "postgresql://relay:private-password@db.invalid:6543/postgres"
REMOTE_PEPPER = "hosted-runtime-pepper-that-must-not-be-used"


def clear_relay_environment(monkeypatch):
    for name in (
        TEST_DATABASE_URL_ENV,
        TEST_PEPPER_ENV,
        RUNTIME_DATABASE_URL_ENV,
        RUNTIME_PEPPER_ENV,
    ):
        monkeypatch.delenv(name, raising=False)


def test_missing_relay_database_configuration_skips_safely(monkeypatch):
    clear_relay_environment(monkeypatch)

    with pytest.raises(pytest.skip.Exception) as skipped:
        relay_test_config_or_skip()

    assert str(skipped.value) == UNAVAILABLE_REASON


def test_loopback_runtime_configuration_remains_a_local_development_fallback():
    config = resolve_relay_test_config(
        {
            RUNTIME_DATABASE_URL_ENV: LOCAL_URL,
            RUNTIME_PEPPER_ENV: LOCAL_PEPPER,
        }
    )

    assert config is not None
    assert config.database_url == LOCAL_URL
    assert config.pepper == LOCAL_PEPPER


def test_explicit_loopback_test_configuration_takes_precedence():
    config = resolve_relay_test_config(
        {
            TEST_DATABASE_URL_ENV: LOCAL_URL,
            TEST_PEPPER_ENV: LOCAL_PEPPER,
            RUNTIME_DATABASE_URL_ENV: REMOTE_URL,
            RUNTIME_PEPPER_ENV: REMOTE_PEPPER,
        }
    )

    assert config is not None
    assert config.database_url == LOCAL_URL
    assert config.pepper == LOCAL_PEPPER


@pytest.mark.parametrize(
    "url",
    [
        REMOTE_URL,
        "postgresql://relay:secret@example.invalid/postgres",
        "postgresql://relay:secret@localhost.example/postgres",
        "postgresql://relay:secret@[::2]:55432/postgres",
        "not-a-database-url",
    ],
)
def test_non_loopback_explicit_test_database_url_is_rejected(url):
    assert resolve_relay_test_config(
        {TEST_DATABASE_URL_ENV: url, TEST_PEPPER_ENV: LOCAL_PEPPER}
    ) is None


def test_rejected_runtime_url_never_reaches_psycopg_connect(monkeypatch):
    clear_relay_environment(monkeypatch)
    monkeypatch.setenv(RUNTIME_DATABASE_URL_ENV, REMOTE_URL)
    monkeypatch.setenv(RUNTIME_PEPPER_ENV, REMOTE_PEPPER)
    calls = []
    monkeypatch.setattr(
        test_mobile_relay_schema.psycopg,
        "connect",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    with pytest.raises(pytest.skip.Exception) as skipped:
        test_mobile_relay_schema._relay_database_connection()

    assert calls == []
    reason = str(skipped.value)
    assert reason == UNAVAILABLE_REASON
    for secret in (REMOTE_URL, "private-password", REMOTE_PEPPER, "db.invalid"):
        assert secret not in reason


def test_runtime_pepper_is_not_returned_with_rejected_runtime_url():
    assert resolve_relay_test_config(
        {
            RUNTIME_DATABASE_URL_ENV: REMOTE_URL,
            RUNTIME_PEPPER_ENV: REMOTE_PEPPER,
        }
    ) is None


def test_runtime_pepper_is_not_paired_with_explicit_test_url():
    assert resolve_relay_test_config(
        {
            TEST_DATABASE_URL_ENV: LOCAL_URL,
            RUNTIME_DATABASE_URL_ENV: REMOTE_URL,
            RUNTIME_PEPPER_ENV: REMOTE_PEPPER,
        }
    ) is None


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://relay:secret@localhost:55432/postgres",
        "postgresql://relay:secret@127.99.1.2:55432/postgres",
        "postgresql://relay:secret@[::1]:55432/postgres",
    ],
)
def test_all_documented_loopback_host_forms_are_allowed(url):
    assert resolve_relay_test_config(
        {TEST_DATABASE_URL_ENV: url, TEST_PEPPER_ENV: LOCAL_PEPPER}
    ) is not None
