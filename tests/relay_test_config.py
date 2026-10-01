"""Safe, centralized configuration for relay database integration tests."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import os
from collections.abc import Mapping
from urllib.parse import urlsplit

import pytest


TEST_DATABASE_URL_ENV = "FLIGHTMARGIN_RELAY_TEST_DATABASE_URL"
TEST_PEPPER_ENV = "FLIGHTMARGIN_RELAY_TEST_PEPPER"
RUNTIME_DATABASE_URL_ENV = "FLIGHTMARGIN_RELAY_DATABASE_URL"
RUNTIME_PEPPER_ENV = "FLIGHTMARGIN_RELAY_PEPPER"
UNAVAILABLE_REASON = (
    "relay integration tests require an explicitly configured local database"
)


@dataclass(frozen=True)
class RelayTestConfig:
    database_url: str
    pepper: str


def _is_loopback_database_url(value: str) -> bool:
    """Return whether a URL syntactically names an allowed loopback host."""
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
    except ValueError:
        return False
    if parsed.scheme not in {"postgres", "postgresql"} or not hostname:
        return False
    if hostname.lower() == "localhost":
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv4Address):
        return address.packed[0] == 127
    return address == ipaddress.IPv6Address("::1")


def resolve_relay_test_config(
    environment: Mapping[str, str] | None = None,
) -> RelayTestConfig | None:
    """Resolve test-only credentials without ever returning a remote DB URL."""
    environment = os.environ if environment is None else environment
    explicit_url = environment.get(TEST_DATABASE_URL_ENV)
    explicit_pepper = environment.get(TEST_PEPPER_ENV)
    runtime_url = environment.get(RUNTIME_DATABASE_URL_ENV)
    runtime_pepper = environment.get(RUNTIME_PEPPER_ENV)
    if explicit_url is not None or explicit_pepper is not None:
        database_url = explicit_url
        pepper = explicit_pepper
    else:
        database_url = runtime_url
        pepper = runtime_pepper
    if not database_url or not _is_loopback_database_url(database_url):
        return None
    if not pepper:
        return None
    return RelayTestConfig(database_url=database_url, pepper=pepper)


def relay_test_config_or_skip() -> RelayTestConfig:
    config = resolve_relay_test_config()
    if config is None:
        pytest.skip(UNAVAILABLE_REASON)
    return config
