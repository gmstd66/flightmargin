"""Latest-only relay synchronization and user-initiated pairing coordination."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import platform
import socket
import time

from app.mobile_relay.client import RelayClient, RelayClientError
from app.mobile_relay.config import RelaySettingsStore
from app.mobile_relay.identity import HostIdentityStore, IdentityStorageError


APPROVED_QUOTA_FIELDS = (
    "schema_version",
    "sampled_at",
    "five_hour_used",
    "five_hour_reset_at",
    "weekly_used",
    "weekly_reset_at",
    "plan_type",
    "reset_credits_available",
    "credits_balance",
    "spend_control_reached",
    "rate_limit_reached_type",
    "collector_state",
    "collector_message_code",
)
DEFAULT_BACKOFF_SECONDS = (2, 5, 15, 30, 60, 300)


class PairingUnavailable(RuntimeError):
    pass


def _iso_timestamp(value):
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def quota_payload(sample: dict) -> dict:
    """Copy only the relay-approved normalized v1 boundary."""
    balance = sample.get("credits_balance")
    if balance is not None:
        balance = float(balance)
    payload = {
        "schema_version": 1,
        "sampled_at": _iso_timestamp(sample["captured_at"]),
        "five_hour_used": sample.get("five_hour_used"),
        "five_hour_reset_at": _iso_timestamp(sample.get("five_hour_reset_at")),
        "weekly_used": sample.get("weekly_used"),
        "weekly_reset_at": _iso_timestamp(sample.get("weekly_reset_at")),
        "plan_type": sample.get("plan_type"),
        "reset_credits_available": sample.get("reset_credits_available"),
        "credits_balance": balance,
        "spend_control_reached": bool(sample.get("spend_control_reached", False)),
        "rate_limit_reached_type": sample.get("rate_limit_reached_type"),
        "collector_state": "ok",
        "collector_message_code": None,
    }
    assert tuple(payload) == APPROVED_QUOTA_FIELDS
    return payload


class RelayCoordinator:
    def __init__(
        self,
        settings_store: RelaySettingsStore,
        identity_store: HostIdentityStore,
        *,
        client=None,
        app_version: str,
        backoff_seconds=DEFAULT_BACKOFF_SECONDS,
        wall_time=time.time,
    ):
        self.settings_store = settings_store
        self.identity_store = identity_store
        self.client = client or RelayClient(settings_store.endpoint)
        self.app_version = app_version
        self.backoff_seconds = tuple(backoff_seconds)
        self.wall_time = wall_time
        self.settings = settings_store.load()
        self._registered = False
        self._latest = None
        self._last_uploaded_key = None
        self._attempt = 0
        self._next_retry_at = None
        self._last_error = None
        self._event = asyncio.Event()
        self._task = None
        self._operation_lock = asyncio.Lock()

    async def start(self):
        if self._task is None:
            self._task = asyncio.create_task(self._worker())
        if self.settings.enabled:
            self._event.set()

    async def stop(self):
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def notify_sample(self, sample: dict):
        self._latest = dict(sample)
        if self.settings.enabled:
            self._event.set()

    async def set_enabled(self, enabled: bool):
        async with self._operation_lock:
            enabled = bool(enabled)
            self.settings = replace(self.settings, enabled=enabled)
            self.settings_store.save(self.settings)
            if enabled:
                self._last_error = None
                self._next_retry_at = None
                self._attempt = 0
                self._event.set()
            else:
                self._registered = False
                self._next_retry_at = None
                self._attempt = 0
                self._last_error = None
                self._event.set()

    def public_status(self) -> dict:
        if not self.settings.enabled:
            state = "Disabled"
        elif self._last_error:
            state = "Offline / Retry scheduled"
        elif self._registered:
            state = "Connected"
        else:
            state = "Registering"
        return {
            "enabled": self.settings.enabled,
            "endpoint": self.settings_store.endpoint,
            "state": state,
            "registered": self._registered,
            "last_successful_upload": self.settings.last_successful_upload,
            "last_error": self._last_error,
            "next_retry_at": self._next_retry_at,
        }

    def _record_failure(self, message: str):
        delay = self.backoff_seconds[min(self._attempt, len(self.backoff_seconds) - 1)]
        self._attempt += 1
        self._next_retry_at = int(self.wall_time() + delay)
        self._last_error = message

    def _record_success(self):
        self._attempt = 0
        self._next_retry_at = None
        self._last_error = None

    def _sync_latest(self):
        if not self.settings.enabled or self._latest is None:
            return True
        identity = self.identity_store.load_or_create()
        if not self._registered:
            system_name = platform.system().lower()
            platform_name = "windows" if system_name == "windows" else "linux"
            self.client.register_host(
                identity,
                display_name=socket.gethostname()[:120] or "FlightMargin host",
                platform_name=platform_name,
                app_version=self.app_version,
            )
            self._registered = True
            self.settings = replace(
                self.settings,
                registered=True,
                registered_endpoint=self.settings_store.endpoint,
            )
            self.settings_store.save(self.settings)
        sample_key = (self._latest.get("id"), self._latest.get("captured_at"))
        if sample_key == self._last_uploaded_key:
            return True
        self.client.upload_quota(identity.credential, quota_payload(self._latest))
        self._last_uploaded_key = sample_key
        now = int(self.wall_time())
        self.settings = replace(self.settings, last_successful_upload=now)
        self.settings_store.save(self.settings)
        return True

    async def sync_once(self) -> bool:
        async with self._operation_lock:
            try:
                await asyncio.to_thread(self._sync_latest)
            except IdentityStorageError:
                self._record_failure("Local relay identity is unavailable.")
                return False
            except RelayClientError as exc:
                if exc.status_code in {401, 403}:
                    self._registered = False
                    message = "Relay authentication failed. Retry scheduled."
                elif exc.status_code == 409:
                    message = "Host registration was rejected. Retry scheduled."
                else:
                    message = "Relay unavailable. Retry scheduled."
                self._record_failure(message)
                return False
            except Exception:
                self._record_failure("Relay unavailable. Retry scheduled.")
                return False
            self._record_success()
            return True

    async def _worker(self):
        while True:
            await self._event.wait()
            self._event.clear()
            while self.settings.enabled and self._latest is not None:
                if self._next_retry_at is not None:
                    delay = max(0, self._next_retry_at - self.wall_time())
                    try:
                        await asyncio.wait_for(self._event.wait(), timeout=delay)
                        self._event.clear()
                        if not self.settings.enabled:
                            break
                        continue
                    except asyncio.TimeoutError:
                        pass
                if await self.sync_once():
                    break

    async def request_pairing(self) -> dict:
        if not self.settings.enabled:
            raise PairingUnavailable("Mobile Relay is disabled.")
        if not self._registered or self._last_error:
            raise PairingUnavailable("Mobile Relay is not connected.")
        async with self._operation_lock:
            try:
                identity = await asyncio.to_thread(self.identity_store.load_or_create)
                return await asyncio.to_thread(
                    self.client.create_pairing, identity.credential
                )
            except IdentityStorageError:
                self._record_failure("Relay unavailable. Retry scheduled.")
                self._event.set()
                raise PairingUnavailable("Unable to create a pairing session.") from None
            except RelayClientError as exc:
                if exc.status_code in {401, 403}:
                    self._registered = False
                self._record_failure("Relay unavailable. Retry scheduled.")
                self._event.set()
                raise PairingUnavailable("Unable to create a pairing session.") from None
            except Exception:
                self._record_failure("Relay unavailable. Retry scheduled.")
                self._event.set()
                raise PairingUnavailable("Unable to create a pairing session.") from None
