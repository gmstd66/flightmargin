import asyncio
import json
import re
import stat
from urllib.error import URLError

import pytest

from app.mobile_relay.client import RelayClient, RelayClientError
from app.mobile_relay.config import (
    PRODUCTION_RELAY_ENDPOINT,
    RelaySettings,
    RelaySettingsStore,
    validate_endpoint,
)
from app.mobile_relay.identity import (
    CredentialProtector,
    HostIdentityStore,
    IdentityStorageError,
)
from app.mobile_relay.sync import (
    APPROVED_QUOTA_FIELDS,
    PairingUnavailable,
    RelayCoordinator,
    quota_payload,
)
from app.version import __version__


def sample(captured_at=1788990000, sample_id=1):
    return {
        "id": sample_id,
        "captured_at": captured_at,
        "five_hour_used": 42.5,
        "five_hour_reset_at": 1788999919,
        "weekly_used": 25,
        "weekly_reset_at": 1789494339,
        "plan_type": "plus",
        "reset_credits_available": 3,
        "credits_balance": "12.5000",
        "spend_control_reached": 0,
        "rate_limit_reached_type": None,
        "local_only": "must not leave this host",
    }


class ReversibleTestProtector(CredentialProtector):
    prefix = b"protected:"

    def protect(self, plaintext):
        return self.prefix + plaintext[::-1]

    def unprotect(self, protected):
        if not protected.startswith(self.prefix):
            raise IdentityStorageError("invalid protected value")
        return protected[len(self.prefix) :][::-1]


def test_identity_is_created_once_and_stable_across_restart(tmp_path):
    first = HostIdentityStore(tmp_path, system="linux").load_or_create()
    second = HostIdentityStore(tmp_path, system="linux").load_or_create()

    assert first == second
    assert re.fullmatch(
        r"fmh1\.[0-9a-f-]{36}\.[A-Za-z0-9_-]{43}", first.credential
    )


def test_linux_identity_file_is_owner_only(tmp_path):
    store = HostIdentityStore(tmp_path, system="linux")
    store.load_or_create()

    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600


def test_windows_storage_uses_protector_and_does_not_write_plaintext(tmp_path):
    protector = ReversibleTestProtector()
    store = HostIdentityStore(tmp_path, system="windows", protector=protector)
    identity = store.load_or_create()
    on_disk = store.path.read_text(encoding="utf-8")

    assert identity.credential not in on_disk
    assert "protected_credential" in on_disk
    assert HostIdentityStore(
        tmp_path, system="windows", protector=protector
    ).load_or_create() == identity


@pytest.mark.parametrize(
    "contents",
    ["not-json", '{"schema_version":1,"host_id":"bad","credential":"bad"}'],
)
def test_malformed_identity_fails_without_rotation(tmp_path, contents):
    store = HostIdentityStore(tmp_path, system="linux")
    store.path.write_text(contents, encoding="utf-8")

    with pytest.raises(IdentityStorageError, match="identity is invalid"):
        store.load_or_create()
    assert store.path.read_text(encoding="utf-8") == contents


def test_relay_configuration_defaults_disabled(tmp_path):
    store = RelaySettingsStore(tmp_path, endpoint_override=PRODUCTION_RELAY_ENDPOINT)
    assert store.load() == RelaySettings()
    assert store.endpoint == PRODUCTION_RELAY_ENDPOINT


@pytest.mark.parametrize(
    "endpoint",
    [PRODUCTION_RELAY_ENDPOINT, "https://relay.example.test/base"],
)
def test_https_endpoints_are_accepted(endpoint):
    assert validate_endpoint(endpoint) == endpoint


@pytest.mark.parametrize(
    "endpoint",
    ["http://example.com/relay", "http://192.168.1.20:18093", "ftp://127.0.0.1/x"],
)
def test_non_loopback_cleartext_endpoint_is_rejected(endpoint):
    with pytest.raises(ValueError):
        validate_endpoint(endpoint)


@pytest.mark.parametrize(
    "endpoint",
    ["http://127.0.0.1:18093", "http://localhost:18093", "http://[::1]:18093"],
)
def test_loopback_development_endpoint_is_accepted(endpoint):
    assert validate_endpoint(endpoint) == endpoint


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = json.dumps(payload).encode()
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, amount):
        return self.payload


class RecordingOpener:
    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [])
        self.error = error
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        if self.error:
            raise self.error
        return FakeResponse(self.responses.pop(0))


def test_registration_request_shape_and_idempotent_response(tmp_path):
    identity = HostIdentityStore(tmp_path, system="linux").load_or_create()
    opener = RecordingOpener(
        [{"host_id": identity.host_id, "result": "already_registered"}]
    )
    client = RelayClient("http://127.0.0.1:18093", opener=opener)

    client.register_host(
        identity, display_name="test-host", platform_name="linux", app_version=__version__
    )

    request, timeout = opener.requests[0]
    assert request.full_url.endswith("/v1/hosts/register")
    assert request.method == "POST"
    assert timeout == 5.0
    assert json.loads(request.data) == {
        "host_id": identity.host_id,
        "display_name": "test-host",
        "platform": "linux",
        "app_version": __version__,
        "credential": identity.credential,
    }
    assert request.get_header("Authorization") is None


def test_quota_upload_uses_bearer_and_exact_approved_payload(tmp_path):
    identity = HostIdentityStore(tmp_path, system="linux").load_or_create()
    opener = RecordingOpener([{"result": "accepted"}])
    client = RelayClient("http://127.0.0.1:18093", opener=opener)
    payload = quota_payload(sample())

    client.upload_quota(identity.credential, payload)

    request, _ = opener.requests[0]
    assert request.get_header("Authorization") == f"Bearer {identity.credential}"
    assert tuple(json.loads(request.data)) == APPROVED_QUOTA_FIELDS
    assert "local_only" not in request.data.decode()
    assert payload["sampled_at"] == "2026-09-09T21:40:00Z"
    assert payload["credits_balance"] == 12.5


def test_transport_failure_is_sanitized_and_does_not_include_url_or_secret():
    opener = RecordingOpener(error=URLError("private network detail"))
    client = RelayClient("http://127.0.0.1:18093", opener=opener)

    with pytest.raises(RelayClientError) as captured:
        client.upload_quota("fmh1.secret", quota_payload(sample()))
    assert str(captured.value) == "Relay is unavailable"
    assert "private" not in str(captured.value)
    assert "fmh1" not in str(captured.value)


def test_pairing_response_requires_matching_deep_link():
    opener = RecordingOpener(
        [{
            "pairing_token": "fmp1.session.secret",
            "manual_code": "ABCDE-FGHIJ",
            "expires_at": "2026-09-30T12:05:00Z",
            "deep_link": "https://unexpected.example/",
        }]
    )
    client = RelayClient("http://127.0.0.1:18093", opener=opener)

    with pytest.raises(RelayClientError, match="invalid response"):
        client.create_pairing("fmh1.secret")


class FakeRelayClient:
    def __init__(self, *, fail_registration=False, fail_uploads=0):
        self.fail_registration = fail_registration
        self.fail_uploads = fail_uploads
        self.registrations = []
        self.uploads = []
        self.pairings = 0

    def register_host(self, identity, **metadata):
        self.registrations.append((identity, metadata))
        if self.fail_registration:
            raise RelayClientError("sensitive transport cause")
        return {"host_id": identity.host_id, "result": "registered"}

    def upload_quota(self, credential, payload):
        self.uploads.append((credential, payload))
        if self.fail_uploads:
            self.fail_uploads -= 1
            raise RelayClientError("sensitive transport cause")
        return {"result": "accepted"}

    def create_pairing(self, credential):
        self.pairings += 1
        return {
            "pairing_token": "fmp1.session.secret",
            "manual_code": "ABCDE-FGHIJ",
            "expires_at": "2026-09-30T12:05:00Z",
            "deep_link": "flightmargin://pair/v1?token=fmp1.session.secret",
        }


def coordinator(tmp_path, client, *, now=lambda: 1000, backoff=(2, 5, 15)):
    settings = RelaySettingsStore(
        tmp_path, endpoint_override="http://127.0.0.1:18093"
    )
    return RelayCoordinator(
        settings,
        HostIdentityStore(tmp_path, system="linux"),
        client=client,
        app_version=__version__,
        backoff_seconds=backoff,
        wall_time=now,
    )


def test_registration_failure_does_not_rotate_identity_and_is_sanitized(tmp_path):
    client = FakeRelayClient(fail_registration=True)
    sync = coordinator(tmp_path, client)
    asyncio.run(sync.set_enabled(True))
    sync.notify_sample(sample())

    assert asyncio.run(sync.sync_once()) is False
    first = sync.identity_store.load()
    assert asyncio.run(sync.sync_once()) is False
    assert sync.identity_store.load() == first
    assert sync.public_status()["last_error"] == "Relay unavailable. Retry scheduled."
    assert "sensitive" not in json.dumps(sync.public_status())


def test_backoff_progresses_and_success_resets_it(tmp_path):
    current = [1000]
    client = FakeRelayClient(fail_uploads=2)
    sync = coordinator(tmp_path, client, now=lambda: current[0])
    asyncio.run(sync.set_enabled(True))
    sync.notify_sample(sample())

    assert asyncio.run(sync.sync_once()) is False
    assert sync.public_status()["next_retry_at"] == 1002
    assert asyncio.run(sync.sync_once()) is False
    assert sync.public_status()["next_retry_at"] == 1005
    assert asyncio.run(sync.sync_once()) is True
    assert sync.public_status()["next_retry_at"] is None
    assert sync.public_status()["state"] == "Connected"


def test_repeated_sample_is_not_uploaded_twice(tmp_path):
    client = FakeRelayClient()
    sync = coordinator(tmp_path, client)
    asyncio.run(sync.set_enabled(True))
    sync.notify_sample(sample())

    assert asyncio.run(sync.sync_once()) is True
    assert asyncio.run(sync.sync_once()) is True
    assert len(client.registrations) == 1
    assert len(client.uploads) == 1


def test_relay_failure_does_not_change_local_sample(tmp_path):
    original = sample()
    client = FakeRelayClient(fail_uploads=1)
    sync = coordinator(tmp_path, client)
    asyncio.run(sync.set_enabled(True))
    sync.notify_sample(original)

    assert asyncio.run(sync.sync_once()) is False
    assert original["local_only"] == "must not leave this host"


def test_pairing_requires_explicit_request_and_is_never_persisted(tmp_path):
    client = FakeRelayClient()
    sync = coordinator(tmp_path, client)
    asyncio.run(sync.set_enabled(True))
    sync.notify_sample(sample())
    asyncio.run(sync.sync_once())
    assert client.pairings == 0

    pairing = asyncio.run(sync.request_pairing())

    assert pairing["manual_code"] == "ABCDE-FGHIJ"
    assert pairing["deep_link"].endswith(pairing["pairing_token"])
    assert client.pairings == 1
    persisted = "".join(
        path.read_text(encoding="utf-8")
        for path in tmp_path.iterdir()
        if path.is_file()
    )
    assert pairing["pairing_token"] not in persisted
    assert pairing["manual_code"] not in persisted


def test_pairing_disabled_and_offline_states_are_safe(tmp_path):
    sync = coordinator(tmp_path, FakeRelayClient())
    with pytest.raises(PairingUnavailable, match="disabled"):
        asyncio.run(sync.request_pairing())
    asyncio.run(sync.set_enabled(True))
    with pytest.raises(PairingUnavailable, match="not connected"):
        asyncio.run(sync.request_pairing())


def test_disabling_stops_sync_but_keeps_identity(tmp_path):
    client = FakeRelayClient()
    sync = coordinator(tmp_path, client)
    asyncio.run(sync.set_enabled(True))
    sync.notify_sample(sample())
    asyncio.run(sync.sync_once())
    identity = sync.identity_store.load()

    asyncio.run(sync.set_enabled(False))
    sync.notify_sample(sample(captured_at=1788991000, sample_id=2))
    asyncio.run(sync.sync_once())

    assert len(client.uploads) == 1
    assert sync.identity_store.load() == identity
    assert sync.public_status()["state"] == "Disabled"
