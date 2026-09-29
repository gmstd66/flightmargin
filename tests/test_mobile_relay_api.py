import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import re
import os
import secrets
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from relay.config import RelayConfig
from relay.credentials import credential_digest, parse_credential
from relay.database import RelayDatabase
from relay.main import create_app


def make_credential(kind, credential_id=None, secret_bytes=None):
    prefixes = {"host": "fmh1", "device": "fmd1"}
    credential_id = credential_id or uuid4()
    secret_bytes = secret_bytes or secrets.token_bytes(32)
    secret = base64.urlsafe_b64encode(secret_bytes).rstrip(b"=").decode("ascii")
    return f"{prefixes[kind]}.{credential_id}.{secret}"


def registration_payload(host_id=None, credential=None):
    return {
        "host_id": str(host_id or uuid4()),
        "display_name": "Test host",
        "platform": "linux",
        "app_version": "test",
        "credential": credential or make_credential("host"),
    }


def quota_payload(sampled_at=None, five_hour_used=42.5):
    sampled_at = sampled_at or datetime.now(timezone.utc)
    return {
        "schema_version": 1,
        "sampled_at": sampled_at.isoformat().replace("+00:00", "Z"),
        "five_hour_used": five_hour_used,
        "five_hour_reset_at": (sampled_at + timedelta(hours=2)).isoformat(),
        "weekly_used": 78.0,
        "weekly_reset_at": (sampled_at + timedelta(days=2)).isoformat(),
        "plan_type": "plus",
        "reset_credits_available": 3,
        "credits_balance": 12.5,
        "spend_control_reached": False,
        "rate_limit_reached_type": None,
        "collector_state": "ok",
        "collector_message_code": None,
    }


def pairing_claim_payload(pairing_token=None, manual_code=None, **overrides):
    payload = {
        "device_id": str(uuid4()),
        "display_name": "Test iPhone",
        "platform": "ios",
        "credential": make_credential("device"),
    }
    if pairing_token is not None:
        payload["pairing_token"] = pairing_token
    if manual_code is not None:
        payload["manual_code"] = manual_code
    payload.update(overrides)
    return payload


def test_relay_config_rejects_short_pepper_without_exposing_it(monkeypatch):
    short_pepper = "too-short-and-private"
    monkeypatch.setenv(
        "FLIGHTMARGIN_RELAY_DATABASE_URL", "postgresql://unused"
    )
    monkeypatch.setenv("FLIGHTMARGIN_RELAY_PEPPER", short_pepper)

    with pytest.raises(ValueError) as error:
        RelayConfig.from_environment()

    assert "at least 32 bytes" in str(error.value)
    assert short_pepper not in str(error.value)


def test_relay_config_counts_utf8_bytes_for_pepper(monkeypatch):
    monkeypatch.setenv(
        "FLIGHTMARGIN_RELAY_DATABASE_URL", "postgresql://unused"
    )
    monkeypatch.setenv("FLIGHTMARGIN_RELAY_PEPPER", "é" * 16)

    config = RelayConfig.from_environment()

    assert len(config.pepper) == 32


def test_runtime_database_connections_use_five_second_timeout(monkeypatch):
    captured = {}

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_connect(database_url, **kwargs):
        captured["database_url"] = database_url
        captured.update(kwargs)
        return FakeConnection()

    monkeypatch.setattr("relay.database.psycopg.connect", fake_connect)
    config = RelayConfig(database_url="postgresql://unused", pepper=b"x" * 32)

    with RelayDatabase(config).connect():
        pass

    assert captured["database_url"] == "postgresql://unused"
    assert captured["connect_timeout"] == 5


@pytest.fixture
def validation_client():
    config = RelayConfig(database_url="postgresql://unused", pepper=b"x" * 32)
    with TestClient(create_app(config)) as client:
        yield client


@pytest.mark.parametrize("field", ["display_name", "platform"])
def test_registration_rejects_whitespace_only_identity_fields(
    validation_client, field
):
    payload = registration_payload()
    payload[field] = " \t "

    response = validation_client.post("/v1/hosts/register", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("app_version", "v" * 65),
        ("credential", "x" * 129),
    ],
)
def test_registration_enforces_public_string_limits(
    validation_client, field, value
):
    payload = registration_payload()
    payload[field] = value

    response = validation_client.post("/v1/hosts/register", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("plan_type", "p" * 65),
        ("rate_limit_reached_type", "r" * 65),
        ("collector_message_code", "c" * 129),
    ],
)
def test_quota_enforces_public_string_limits(validation_client, field, value):
    payload = quota_payload()
    payload[field] = value

    response = validation_client.put("/v1/quota", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("five_hour_used", "42.5"),
        ("reset_credits_available", "3"),
        ("spend_control_reached", 0),
    ],
)
def test_quota_rejects_coerced_scalar_types(validation_client, field, value):
    payload = quota_payload()
    payload[field] = value

    response = validation_client.put("/v1/quota", json=payload)

    assert response.status_code == 422


@pytest.fixture
def relay_context():
    database_url = os.environ.get("FLIGHTMARGIN_RELAY_DATABASE_URL")
    pepper = os.environ.get("FLIGHTMARGIN_RELAY_PEPPER")
    if not database_url or not pepper:
        pytest.skip("local relay PostgreSQL configuration is unavailable")

    config = RelayConfig(database_url=database_url, pepper=pepper.encode("utf-8"))
    host_ids = []
    with TestClient(create_app(config)) as client:
        yield client, config, host_ids

    if host_ids:
        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("delete from relay_hosts where id = any(%s)", (host_ids,))


def register(relay_context, *, host_id=None, credential=None):
    client, _config, host_ids = relay_context
    payload = registration_payload(host_id=host_id, credential=credential)
    host_ids.append(payload["host_id"])
    response = client.post("/v1/hosts/register", json=payload)
    assert response.status_code == 201
    return payload, response


def seed_device(config, host_id, credential, revoked=False):
    device_id = uuid4()
    parsed = parse_credential(credential, "device")
    digest = credential_digest(parsed, config.pepper)
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into relay_devices (
                    id, host_id, display_name, platform, revoked_at
                ) values (%s, %s, 'Test iPhone', 'ios', %s)
                """,
                (device_id, host_id, datetime.now(timezone.utc) if revoked else None),
            )
            cursor.execute(
                """
                insert into relay_device_credentials (id, device_id, token_digest)
                values (%s, %s, %s)
                """,
                (parsed.credential_id, device_id, digest),
            )
    return device_id


def test_health_endpoint(relay_context):
    client, _config, _host_ids = relay_context

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_host_registration_and_retry_are_idempotent(relay_context):
    payload, first = register(relay_context)
    client, config, _host_ids = relay_context

    retry = client.post("/v1/hosts/register", json=payload)

    assert first.json() == {
        "api_version": 1,
        "host_id": payload["host_id"],
        "registered": True,
        "result": "registered",
    }
    assert retry.status_code == 201
    assert retry.json() == {
        "api_version": 1,
        "host_id": payload["host_id"],
        "registered": False,
        "result": "already_registered",
    }
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select count(*) from relay_host_credentials where host_id = %s",
                (payload["host_id"],),
            )
            assert cursor.fetchone()[0] == 1


def test_idempotent_registration_keeps_host_metadata_immutable(relay_context):
    payload, _first = register(relay_context)
    client, config, _host_ids = relay_context
    retry_payload = {
        **payload,
        "display_name": "Changed host",
        "platform": "changed-platform",
        "app_version": "changed-version",
    }

    retry = client.post("/v1/hosts/register", json=retry_payload)

    assert retry.status_code == 201
    assert retry.json()["registered"] is False
    assert retry.json()["result"] == "already_registered"
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select display_name, platform, app_version
                from relay_hosts where id = %s
                """,
                (payload["host_id"],),
            )
            assert cursor.fetchone() == ("Test host", "linux", "test")


def test_malformed_host_credential_is_rejected(relay_context):
    client, _config, _host_ids = relay_context
    payload = registration_payload(credential=f"fmd1.{uuid4()}.not-a-host-secret")

    response = client.post("/v1/hosts/register", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == "Malformed host credential"


def test_oversized_bearer_credential_is_rejected(relay_context):
    client, _config, _host_ids = relay_context

    response = client.get(
        "/v1/quota",
        headers={"Authorization": f"Bearer {'x' * 129}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or revoked credential"


def test_conflicting_host_registration_fails_safely(relay_context):
    payload, _response = register(relay_context)
    client, _config, _host_ids = relay_context
    payload["credential"] = make_credential("host")

    response = client.post("/v1/hosts/register", json=payload)

    assert response.status_code == 409


def test_raw_host_credential_secret_is_absent_from_database(relay_context):
    payload, _response = register(relay_context)
    _client, config, _host_ids = relay_context
    raw_secret = payload["credential"].rsplit(".", 1)[1]

    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select row_to_json(h)::text || row_to_json(c)::text
                from relay_hosts h
                join relay_host_credentials c on c.host_id = h.id
                where h.id = %s
                """,
                (payload["host_id"],),
            )
            stored_record = cursor.fetchone()[0]

    assert raw_secret not in stored_record
    assert payload["credential"] not in stored_record


def test_incorrect_host_secret_is_rejected(relay_context):
    payload, _response = register(relay_context)
    client, _config, _host_ids = relay_context
    credential_id = payload["credential"].split(".")[1]
    incorrect = make_credential("host", credential_id=credential_id)

    response = client.put(
        "/v1/quota",
        headers={"Authorization": f"Bearer {incorrect}"},
        json=quota_payload(),
    )

    assert response.status_code == 401


def test_quota_schema_and_percentage_are_validated(relay_context):
    payload, _response = register(relay_context)
    client, _config, _host_ids = relay_context
    headers = {"Authorization": f"Bearer {payload['credential']}"}
    invalid_schema = quota_payload()
    invalid_schema["schema_version"] = True
    invalid_percentage = quota_payload()
    invalid_percentage["weekly_used"] = 101

    assert client.put(
        "/v1/quota", headers=headers, json=invalid_schema
    ).status_code == 422
    assert client.put(
        "/v1/quota", headers=headers, json=invalid_percentage
    ).status_code == 422


def test_revoked_host_credential_is_rejected(relay_context):
    payload, _response = register(relay_context)
    client, config, _host_ids = relay_context
    credential_id = payload["credential"].split(".")[1]
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "update relay_host_credentials set revoked_at = now() where id = %s",
                (credential_id,),
            )

    response = client.put(
        "/v1/quota",
        headers={"Authorization": f"Bearer {payload['credential']}"},
        json=quota_payload(),
    )

    assert response.status_code == 401


def test_accepted_quota_update(relay_context):
    payload, _response = register(relay_context)
    client, config, _host_ids = relay_context
    sampled_at = datetime.now(timezone.utc)
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select last_seen_at from relay_hosts where id = %s",
                (payload["host_id"],),
            )
            previous_last_seen = cursor.fetchone()[0]

    response = client.put(
        "/v1/quota",
        headers={"Authorization": f"Bearer {payload['credential']}"},
        json=quota_payload(sampled_at, five_hour_used=37.25),
    )

    assert response.status_code == 200
    assert response.json()["result"] == "accepted"
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select q.five_hour_used, h.last_seen_at, c.last_used_at
                from relay_quota_state q
                join relay_hosts h on h.id = q.host_id
                join relay_host_credentials c on c.host_id = h.id
                where q.host_id = %s
                """,
                (payload["host_id"],),
            )
            stored_used, last_seen_at, last_used_at = cursor.fetchone()
            assert float(stored_used) == 37.25
            assert last_seen_at > previous_last_seen
            assert last_used_at is not None


def test_stale_quota_update_does_not_overwrite_newer_data(relay_context):
    payload, _response = register(relay_context)
    client, config, _host_ids = relay_context
    newer = datetime.now(timezone.utc)
    older = newer - timedelta(minutes=5)
    headers = {"Authorization": f"Bearer {payload['credential']}"}

    accepted = client.put(
        "/v1/quota", headers=headers, json=quota_payload(newer, 55.0)
    )
    stale = client.put(
        "/v1/quota", headers=headers, json=quota_payload(older, 1.0)
    )

    assert accepted.json()["result"] == "accepted"
    assert stale.status_code == 200
    assert stale.json()["result"] == "stale"
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select count(*), min(sampled_at), min(five_hour_used)
                from relay_quota_state where host_id = %s
                """,
                (payload["host_id"],),
            )
            row_count, stored_sampled_at, stored_used = cursor.fetchone()
    assert row_count == 1
    assert stored_sampled_at == newer
    assert float(stored_used) == 55.0


def test_valid_paired_device_reads_latest_quota(relay_context):
    payload, _response = register(relay_context)
    client, config, _host_ids = relay_context
    host_headers = {"Authorization": f"Bearer {payload['credential']}"}
    assert client.put(
        "/v1/quota", headers=host_headers, json=quota_payload(five_hour_used=61.5)
    ).json()["result"] == "accepted"
    device_credential = make_credential("device")
    device_id = seed_device(config, payload["host_id"], device_credential)

    response = client.get(
        "/v1/quota",
        headers={"Authorization": f"Bearer {device_credential}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"api_version", "host", "quota"}
    assert body["api_version"] == 1
    assert body["host"]["id"] == payload["host_id"]
    assert body["host"]["display_name"] == "Test host"
    assert body["quota"]["five_hour_used"] == 61.5
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select d.last_seen_at, c.last_used_at
                from relay_devices d
                join relay_device_credentials c on c.device_id = d.id
                where d.id = %s
                """,
                (device_id,),
            )
            assert all(value is not None for value in cursor.fetchone())


def test_incorrect_device_secret_is_rejected(relay_context):
    payload, _response = register(relay_context)
    client, config, _host_ids = relay_context
    credential_id = uuid4()
    device_credential = make_credential("device", credential_id=credential_id)
    seed_device(config, payload["host_id"], device_credential)
    incorrect = make_credential("device", credential_id=credential_id)

    response = client.get(
        "/v1/quota",
        headers={"Authorization": f"Bearer {incorrect}"},
    )

    assert response.status_code == 401


def test_revoked_device_is_rejected(relay_context):
    payload, _response = register(relay_context)
    client, config, _host_ids = relay_context
    device_credential = make_credential("device")
    seed_device(config, payload["host_id"], device_credential, revoked=True)

    response = client.get(
        "/v1/quota",
        headers={"Authorization": f"Bearer {device_credential}"},
    )

    assert response.status_code == 401


def create_pairing(relay_context, host_payload):
    client, _config, _host_ids = relay_context
    response = client.post(
        "/v1/pairings",
        headers={"Authorization": f"Bearer {host_payload['credential']}"},
    )
    assert response.status_code == 201
    return response.json()


def test_host_can_create_pairing_with_expected_formats_and_no_raw_secrets(
    relay_context,
):
    host_payload, _response = register(relay_context)
    _client, config, _host_ids = relay_context

    before = datetime.now(timezone.utc)
    pairing = create_pairing(relay_context, host_payload)
    after = datetime.now(timezone.utc)

    token_match = re.fullmatch(
        r"fmp1\.([0-9a-f-]{36})\.([A-Za-z0-9_-]{43})",
        pairing["pairing_token"],
    )
    assert token_match is not None
    assert len(base64.urlsafe_b64decode(token_match.group(2) + "=")) == 32
    assert re.fullmatch(
        r"[0-9A-HJKMNP-TV-Z]{5}-[0-9A-HJKMNP-TV-Z]{5}",
        pairing["manual_code"],
    )
    assert pairing["api_version"] == 1
    assert pairing["deep_link"] == (
        f"flightmargin://pair/v1?token={pairing['pairing_token']}"
    )

    session_id = token_match.group(1)
    expires_at = datetime.fromisoformat(pairing["expires_at"])
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select created_at, expires_at, attempts, max_attempts,
                       row_to_json(p)::text
                from relay_pairing_sessions p where id = %s
                """,
                (session_id,),
            )
            created_at, stored_expires_at, attempts, max_attempts, stored = (
                cursor.fetchone()
            )
    assert before + timedelta(minutes=5) <= expires_at <= after + timedelta(minutes=5)
    assert stored_expires_at == created_at + timedelta(minutes=5)
    assert attempts == 0
    assert max_attempts == 5
    assert token_match.group(2) not in stored
    assert pairing["pairing_token"] not in stored
    assert pairing["manual_code"] not in stored
    assert pairing["manual_code"].replace("-", "") not in stored


def test_unauthenticated_host_cannot_create_pairing(relay_context):
    client, _config, _host_ids = relay_context
    response = client.post("/v1/pairings")
    assert response.status_code == 401


@pytest.mark.parametrize("secret_field", ["pairing_token", "manual_code"])
def test_pairing_claim_succeeds_and_stores_only_device_digest(
    relay_context, secret_field
):
    host_payload, _response = register(relay_context)
    client, config, _host_ids = relay_context
    pairing = create_pairing(relay_context, host_payload)
    claim = pairing_claim_payload(**{secret_field: pairing[secret_field]})

    response = client.post("/v1/pairings/claim", json=claim)

    assert response.status_code == 200
    assert response.json() == {
        "api_version": 1,
        "paired": True,
        "device_id": claim["device_id"],
        "host_id": host_payload["host_id"],
    }
    raw_device_secret = claim["credential"].rsplit(".", 1)[1]
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select count(*), min(c.token_digest),
                       min(row_to_json(d)::text || row_to_json(c)::text)
                from relay_devices d
                join relay_device_credentials c on c.device_id = d.id
                where d.id = %s
                """,
                (claim["device_id"],),
            )
            count, digest, stored = cursor.fetchone()
    assert count == 1
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert claim["credential"] not in stored
    assert raw_device_secret not in stored


@pytest.mark.parametrize(
    "included",
    [(), ("pairing_token", "manual_code")],
)
def test_claim_requires_exactly_one_pairing_method(relay_context, included):
    client, _config, _host_ids = relay_context
    values = {
        "pairing_token": f"fmp1.{uuid4()}.{'A' * 43}",
        "manual_code": "12345-6789A",
    }
    claim = pairing_claim_payload(**{name: values[name] for name in included})
    response = client.post("/v1/pairings/claim", json=claim)
    assert response.status_code == 422


def test_malformed_device_credential_is_rejected(relay_context):
    client, _config, _host_ids = relay_context
    response = client.post(
        "/v1/pairings/claim",
        json=pairing_claim_payload(
            manual_code="12345-6789A", credential="not-a-device-credential"
        ),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Malformed device credential"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("device_id", 1),
        ("display_name", "x" * 121),
        ("platform", "x" * 33),
        ("credential", "x" * 129),
    ],
)
def test_pairing_claim_strictly_bounds_public_fields(
    relay_context, field, value
):
    client, _config, _host_ids = relay_context
    claim = pairing_claim_payload(manual_code="12345-6789A")
    claim[field] = value
    response = client.post("/v1/pairings/claim", json=claim)
    assert response.status_code == 422


def test_incorrect_qr_secret_is_rejected_and_increments_attempts(relay_context):
    host_payload, _response = register(relay_context)
    client, config, _host_ids = relay_context
    pairing = create_pairing(relay_context, host_payload)
    prefix = pairing["pairing_token"].rsplit(".", 1)[0]
    incorrect_token = f"{prefix}.{make_credential('device').rsplit('.', 1)[1]}"

    response = client.post(
        "/v1/pairings/claim",
        json=pairing_claim_payload(pairing_token=incorrect_token),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Pairing could not be completed"
    session_id = pairing["pairing_token"].split(".")[1]
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select attempts from relay_pairing_sessions where id = %s",
                (session_id,),
            )
            assert cursor.fetchone()[0] == 1


def test_incorrect_manual_code_is_rejected_generically(relay_context):
    host_payload, _response = register(relay_context)
    client, _config, _host_ids = relay_context
    pairing = create_pairing(relay_context, host_payload)
    incorrect_code = "00000-00000"
    if pairing["manual_code"] == incorrect_code:
        incorrect_code = "11111-11111"

    response = client.post(
        "/v1/pairings/claim",
        json=pairing_claim_payload(manual_code=incorrect_code),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Pairing could not be completed"


def test_fifth_failed_attempt_exhausts_session_permanently(relay_context):
    host_payload, _response = register(relay_context)
    client, config, _host_ids = relay_context
    pairing = create_pairing(relay_context, host_payload)
    prefix = pairing["pairing_token"].rsplit(".", 1)[0]

    for _ in range(5):
        incorrect = f"{prefix}.{make_credential('device').rsplit('.', 1)[1]}"
        response = client.post(
            "/v1/pairings/claim",
            json=pairing_claim_payload(pairing_token=incorrect),
        )
        assert response.status_code == 400

    correct = client.post(
        "/v1/pairings/claim",
        json=pairing_claim_payload(pairing_token=pairing["pairing_token"]),
    )
    assert correct.status_code == 400
    session_id = pairing["pairing_token"].split(".")[1]
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select attempts from relay_pairing_sessions where id = %s",
                (session_id,),
            )
            assert cursor.fetchone()[0] == 5


def test_expired_pairing_is_rejected(relay_context):
    host_payload, _response = register(relay_context)
    client, config, _host_ids = relay_context
    pairing = create_pairing(relay_context, host_payload)
    session_id = pairing["pairing_token"].split(".")[1]
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "update relay_pairing_sessions set expires_at = now() where id = %s",
                (session_id,),
            )
    response = client.post(
        "/v1/pairings/claim",
        json=pairing_claim_payload(pairing_token=pairing["pairing_token"]),
    )
    assert response.status_code == 400


@pytest.mark.parametrize("secret_field", ["pairing_token", "manual_code"])
def test_same_device_and_credential_retry_is_idempotent(
    relay_context, secret_field
):
    host_payload, _response = register(relay_context)
    client, config, _host_ids = relay_context
    pairing = create_pairing(relay_context, host_payload)
    claim = pairing_claim_payload(**{secret_field: pairing[secret_field]})

    first = client.post("/v1/pairings/claim", json=claim)
    retry = client.post("/v1/pairings/claim", json=claim)

    assert first.status_code == retry.status_code == 200
    assert first.json() == retry.json()
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select count(*) from relay_devices where host_id = %s",
                (host_payload["host_id"],),
            )
            assert cursor.fetchone()[0] == 1


def test_different_device_or_credential_cannot_reclaim_session(relay_context):
    host_payload, _response = register(relay_context)
    client, _config, _host_ids = relay_context
    pairing = create_pairing(relay_context, host_payload)
    claim = pairing_claim_payload(pairing_token=pairing["pairing_token"])
    assert client.post("/v1/pairings/claim", json=claim).status_code == 200

    different_device = pairing_claim_payload(pairing_token=pairing["pairing_token"])
    changed_credential = {**claim, "credential": make_credential("device")}
    assert client.post(
        "/v1/pairings/claim", json=different_device
    ).status_code == 400
    assert client.post(
        "/v1/pairings/claim", json=changed_credential
    ).status_code == 400


def test_newly_paired_device_can_immediately_read_quota(relay_context):
    host_payload, _response = register(relay_context)
    client, _config, _host_ids = relay_context
    host_headers = {"Authorization": f"Bearer {host_payload['credential']}"}
    assert client.put(
        "/v1/quota", headers=host_headers, json=quota_payload(five_hour_used=64.0)
    ).status_code == 200
    pairing = create_pairing(relay_context, host_payload)
    claim = pairing_claim_payload(pairing_token=pairing["pairing_token"])
    assert client.post("/v1/pairings/claim", json=claim).status_code == 200

    quota = client.get(
        "/v1/quota",
        headers={"Authorization": f"Bearer {claim['credential']}"},
    )
    assert quota.status_code == 200
    assert quota.json()["quota"]["five_hour_used"] == 64.0


def test_revoked_host_cannot_create_or_complete_pairing(relay_context):
    first_host, _response = register(relay_context)
    second_host, _response = register(relay_context)
    client, config, _host_ids = relay_context
    pairing = create_pairing(relay_context, first_host)
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "update relay_hosts set revoked_at = now() where id = any(%s)",
                ([first_host["host_id"], second_host["host_id"]],),
            )

    create_response = client.post(
        "/v1/pairings",
        headers={"Authorization": f"Bearer {second_host['credential']}"},
    )
    claim_response = client.post(
        "/v1/pairings/claim",
        json=pairing_claim_payload(pairing_token=pairing["pairing_token"]),
    )
    assert create_response.status_code == 401
    assert claim_response.status_code == 400


def test_concurrent_double_claim_creates_only_one_device(relay_context):
    host_payload, _response = register(relay_context)
    _client, config, _host_ids = relay_context
    pairing = create_pairing(relay_context, host_payload)
    claims = [
        pairing_claim_payload(pairing_token=pairing["pairing_token"]),
        pairing_claim_payload(pairing_token=pairing["pairing_token"]),
    ]

    concurrent_clients = [
        TestClient(create_app(config)),
        TestClient(create_app(config)),
    ]

    def submit(client_and_claim):
        concurrent_client, claim = client_and_claim
        response = concurrent_client.post("/v1/pairings/claim", json=claim)
        return response.status_code

    with concurrent_clients[0], concurrent_clients[1]:
        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(submit, zip(concurrent_clients, claims)))

    assert sorted(statuses) == [200, 400]
    with psycopg.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select count(*) from relay_devices where host_id = %s",
                (host_payload["host_id"],),
            )
            assert cursor.fetchone()[0] == 1
