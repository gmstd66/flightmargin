"""Persistent opt-in state and endpoint policy for mobile relay support."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import ipaddress
import json
import os
from pathlib import Path
from urllib.parse import urlsplit


PRODUCTION_RELAY_ENDPOINT = (
    "https://samcdyrwfwrlxzypzgmj.supabase.co/functions/v1/relay-v1"
)
ENDPOINT_ENVIRONMENT_VARIABLE = "FLIGHTMARGIN_RELAY_ENDPOINT"
SETTINGS_FILE = "mobile-relay.json"


def validate_endpoint(value: str) -> str:
    """Validate a relay base URL without resolving or contacting it."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("Relay endpoint is invalid")
    parsed = urlsplit(value)
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path.endswith("/")
    ):
        raise ValueError("Relay endpoint is invalid")
    if parsed.scheme == "https":
        pass
    elif parsed.scheme == "http":
        hostname = parsed.hostname.lower()
        try:
            is_loopback = ipaddress.ip_address(hostname).is_loopback
        except ValueError:
            is_loopback = hostname == "localhost"
        if not is_loopback:
            raise ValueError("HTTP relay endpoints must be loopback-only")
    else:
        raise ValueError("Relay endpoint must use HTTPS")
    return value


@dataclass(frozen=True)
class RelaySettings:
    enabled: bool = False
    registered: bool = False
    registered_endpoint: str | None = None
    last_successful_upload: int | None = None


class RelaySettingsStore:
    """Keep non-secret relay state beside the application's user data."""

    def __init__(self, data_dir: Path, endpoint_override: str | None = None):
        self.path = Path(data_dir) / SETTINGS_FILE
        candidate = endpoint_override or os.environ.get(
            ENDPOINT_ENVIRONMENT_VARIABLE, PRODUCTION_RELAY_ENDPOINT
        )
        self.endpoint = validate_endpoint(candidate)

    def load(self) -> RelaySettings:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return RelaySettings()
        except (OSError, ValueError, TypeError):
            return RelaySettings()
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            return RelaySettings()
        last_success = raw.get("last_successful_upload")
        registered_endpoint = raw.get("registered_endpoint")
        return RelaySettings(
            enabled=raw.get("enabled") is True,
            registered=raw.get("registered") is True,
            registered_endpoint=(
                registered_endpoint if isinstance(registered_endpoint, str) else None
            ),
            last_successful_upload=(
                last_success if isinstance(last_success, int) and last_success >= 0 else None
            ),
        )

    def save(self, settings: RelaySettings) -> RelaySettings:
        existed = self.path.parent.exists()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not existed and os.name != "nt":
            os.chmod(self.path.parent, 0o700)
        payload = {"schema_version": 1, **asdict(settings)}
        temporary = self.path.with_suffix(".tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.write("\n")
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise
        os.chmod(temporary, 0o600)
        temporary.replace(self.path)
        if os.name != "nt":
            os.chmod(self.path, 0o600)
        return settings
