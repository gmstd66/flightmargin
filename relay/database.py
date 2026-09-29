"""PostgreSQL operations for the FlightMargin mobile relay."""

from contextlib import contextmanager
from datetime import datetime
import hmac
from typing import Iterator
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from relay.config import RelayConfig
from relay.credentials import (
    ParsedCredential,
    ParsedPairingToken,
    credential_digest,
    pairing_manual_digest,
    pairing_qr_digest,
)
from relay.models import HostRegistration, PairingClaim, QuotaReport


class RegistrationConflict(Exception):
    """The requested host or credential identifier is already in conflicting use."""


class AuthenticationFailed(Exception):
    """The supplied credential is unknown, incorrect, or revoked."""


class PairingFailed(Exception):
    """A pairing claim cannot be completed without revealing why."""


class PairingCodeCollision(Exception):
    """A newly generated manual code duplicates an existing code digest."""


class RelayDatabase:
    def __init__(self, config: RelayConfig):
        self.config = config

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        with psycopg.connect(
            self.config.database_url,
            connect_timeout=5,
            row_factory=dict_row,
        ) as connection:
            yield connection

    def register_host(
        self,
        registration: HostRegistration,
        credential: ParsedCredential,
    ) -> bool:
        digest = credential_digest(credential, self.config.pepper)
        host_id = registration.host_id
        credential_id = credential.credential_id

        with self.connect() as connection, connection.cursor() as cursor:
            lock_names = sorted(
                (f"relay-host:{host_id}", f"relay-host-credential:{credential_id}")
            )
            for lock_name in lock_names:
                cursor.execute(
                    "select pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (lock_name,),
                )

            cursor.execute("select id from relay_hosts where id = %s", (host_id,))
            host = cursor.fetchone()
            cursor.execute(
                """
                select id, host_id, token_digest
                from relay_host_credentials
                where id = %s
                """,
                (credential_id,),
            )
            stored_credential = cursor.fetchone()

            if host is None and stored_credential is None:
                cursor.execute(
                    """
                    insert into relay_hosts (id, display_name, platform, app_version)
                    values (%s, %s, %s, %s)
                    """,
                    (
                        host_id,
                        registration.display_name,
                        registration.platform,
                        registration.app_version,
                    ),
                )
                cursor.execute(
                    """
                    insert into relay_host_credentials (id, host_id, token_digest)
                    values (%s, %s, %s)
                    """,
                    (credential_id, host_id, digest),
                )
                return True

            if (
                host is not None
                and stored_credential is not None
                and stored_credential["host_id"] == host_id
                and hmac.compare_digest(stored_credential["token_digest"], digest)
            ):
                return False

            raise RegistrationConflict

    def put_quota(
        self,
        credential: ParsedCredential,
        report: QuotaReport,
    ) -> bool:
        digest = credential_digest(credential, self.config.pepper)
        with self.connect() as connection, connection.cursor() as cursor:
            identity = self._authenticate_host(
                cursor, credential.credential_id, digest
            )
            cursor.execute(
                "update relay_hosts set last_seen_at = now() where id = %s",
                (identity["host_id"],),
            )
            cursor.execute(
                "update relay_host_credentials set last_used_at = now() where id = %s",
                (identity["credential_id"],),
            )
            values = report.model_dump()
            cursor.execute(
                """
                insert into relay_quota_state (
                    host_id, schema_version, sampled_at,
                    five_hour_used, five_hour_reset_at,
                    weekly_used, weekly_reset_at, plan_type,
                    reset_credits_available, credits_balance,
                    spend_control_reached, rate_limit_reached_type,
                    collector_state, collector_message_code
                ) values (
                    %(host_id)s, %(schema_version)s, %(sampled_at)s,
                    %(five_hour_used)s, %(five_hour_reset_at)s,
                    %(weekly_used)s, %(weekly_reset_at)s, %(plan_type)s,
                    %(reset_credits_available)s, %(credits_balance)s,
                    %(spend_control_reached)s, %(rate_limit_reached_type)s,
                    %(collector_state)s, %(collector_message_code)s
                )
                on conflict (host_id) do update set
                    schema_version = excluded.schema_version,
                    sampled_at = excluded.sampled_at,
                    received_at = now(),
                    five_hour_used = excluded.five_hour_used,
                    five_hour_reset_at = excluded.five_hour_reset_at,
                    weekly_used = excluded.weekly_used,
                    weekly_reset_at = excluded.weekly_reset_at,
                    plan_type = excluded.plan_type,
                    reset_credits_available = excluded.reset_credits_available,
                    credits_balance = excluded.credits_balance,
                    spend_control_reached = excluded.spend_control_reached,
                    rate_limit_reached_type = excluded.rate_limit_reached_type,
                    collector_state = excluded.collector_state,
                    collector_message_code = excluded.collector_message_code
                where excluded.sampled_at > relay_quota_state.sampled_at
                returning host_id
                """,
                {"host_id": identity["host_id"], **values},
            )
            return cursor.fetchone() is not None

    def create_pairing(
        self,
        credential: ParsedCredential,
        session_id: UUID,
        qr_digest: str,
        manual_digest: str,
    ) -> datetime:
        digest = credential_digest(credential, self.config.pepper)
        with self.connect() as connection, connection.cursor() as cursor:
            identity = self._authenticate_host(
                cursor, credential.credential_id, digest
            )
            cursor.execute(
                "select pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"relay-pairing-manual:{manual_digest}",),
            )
            cursor.execute(
                "select 1 from relay_pairing_sessions where manual_code_digest = %s",
                (manual_digest,),
            )
            if cursor.fetchone() is not None:
                raise PairingCodeCollision
            cursor.execute(
                "update relay_host_credentials set last_used_at = now() where id = %s",
                (identity["credential_id"],),
            )
            cursor.execute(
                """
                insert into relay_pairing_sessions (
                    id, host_id, qr_secret_digest, manual_code_digest,
                    expires_at, max_attempts
                ) values (%s, %s, %s, %s, now() + interval '5 minutes', 5)
                returning expires_at
                """,
                (session_id, identity["host_id"], qr_digest, manual_digest),
            )
            return cursor.fetchone()["expires_at"]

    def claim_pairing(
        self,
        claim: PairingClaim,
        device_credential: ParsedCredential,
        *,
        pairing_token: ParsedPairingToken | None = None,
        normalized_manual_code: str | None = None,
    ) -> UUID:
        if pairing_token is not None:
            supplied_pairing_digest = pairing_qr_digest(
                pairing_token, self.config.pepper
            )
        else:
            assert normalized_manual_code is not None
            supplied_pairing_digest = pairing_manual_digest(
                normalized_manual_code, self.config.pepper
            )
        supplied_device_digest = credential_digest(
            device_credential, self.config.pepper
        )

        with self.connect() as connection, connection.cursor() as cursor:
            if pairing_token is not None:
                cursor.execute(
                    """
                    select p.*, h.revoked_at as host_revoked_at,
                           p.expires_at > now() as unexpired
                    from relay_pairing_sessions p
                    join relay_hosts h on h.id = p.host_id
                    where p.id = %s
                    for update of p, h
                    """,
                    (pairing_token.session_id,),
                )
            else:
                cursor.execute(
                    """
                    select p.*, h.revoked_at as host_revoked_at,
                           p.expires_at > now() as unexpired
                    from relay_pairing_sessions p
                    join relay_hosts h on h.id = p.host_id
                    where p.manual_code_digest = %s
                    order by p.created_at desc
                    limit 1
                    for update of p, h
                    """,
                    (supplied_pairing_digest,),
                )
            session = cursor.fetchone()
            if session is None:
                hmac.compare_digest("0" * 64, supplied_pairing_digest)
                raise PairingFailed

            expected_digest = (
                session["qr_secret_digest"]
                if pairing_token is not None
                else session["manual_code_digest"]
            )
            secret_matches = hmac.compare_digest(
                expected_digest, supplied_pairing_digest
            )

            if session["claimed_at"] is not None:
                if not secret_matches or session["host_revoked_at"] is not None:
                    raise PairingFailed
                return self._retry_claim(
                    cursor,
                    session,
                    claim.device_id,
                    device_credential.credential_id,
                    supplied_device_digest,
                )

            if (
                session["host_revoked_at"] is not None
                or not session["unexpired"]
                or session["attempts"] >= session["max_attempts"]
            ):
                raise PairingFailed

            if not secret_matches:
                cursor.execute(
                    """
                    update relay_pairing_sessions
                    set attempts = least(attempts + 1, max_attempts)
                    where id = %s
                    """,
                    (session["id"],),
                )
                # Preserve the bounded-attempt update even though the public
                # operation returns an error. The row lock and increment are
                # committed together before the generic failure is raised.
                connection.commit()
                raise PairingFailed

            lock_names = sorted(
                (
                    f"relay-device:{claim.device_id}",
                    f"relay-device-credential:{device_credential.credential_id}",
                )
            )
            for lock_name in lock_names:
                cursor.execute(
                    "select pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (lock_name,),
                )
            cursor.execute(
                "select id from relay_devices where id = %s",
                (claim.device_id,),
            )
            device_exists = cursor.fetchone() is not None
            cursor.execute(
                "select id from relay_device_credentials where id = %s",
                (device_credential.credential_id,),
            )
            credential_exists = cursor.fetchone() is not None
            if device_exists or credential_exists:
                raise PairingFailed

            cursor.execute(
                """
                insert into relay_devices (id, host_id, display_name, platform)
                values (%s, %s, %s, %s)
                """,
                (
                    claim.device_id,
                    session["host_id"],
                    claim.display_name,
                    claim.platform,
                ),
            )
            cursor.execute(
                """
                insert into relay_device_credentials (id, device_id, token_digest)
                values (%s, %s, %s)
                """,
                (
                    device_credential.credential_id,
                    claim.device_id,
                    supplied_device_digest,
                ),
            )
            cursor.execute(
                """
                update relay_pairing_sessions
                set claimed_at = now(), claimed_device_id = %s
                where id = %s
                """,
                (claim.device_id, session["id"]),
            )
            return session["host_id"]

    @staticmethod
    def _retry_claim(
        cursor,
        session: dict,
        device_id: UUID,
        credential_id: UUID,
        supplied_device_digest: str,
    ) -> UUID:
        if session["claimed_device_id"] != device_id:
            raise PairingFailed
        cursor.execute(
            """
            select c.id, c.token_digest
            from relay_devices d
            join relay_device_credentials c on c.device_id = d.id
            where d.id = %s
              and c.id = %s
              and d.host_id = %s
              and d.revoked_at is null
              and c.revoked_at is null
            """,
            (device_id, credential_id, session["host_id"]),
        )
        stored = cursor.fetchone()
        if stored is None or not hmac.compare_digest(
            stored["token_digest"], supplied_device_digest
        ):
            raise PairingFailed
        return session["host_id"]

    def get_quota(self, credential: ParsedCredential) -> dict:
        digest = credential_digest(credential, self.config.pepper)
        with self.connect() as connection, connection.cursor() as cursor:
            identity = self._authenticate_device(
                cursor, credential.credential_id, digest
            )
            cursor.execute(
                "update relay_devices set last_seen_at = now() where id = %s",
                (identity["device_id"],),
            )
            cursor.execute(
                "update relay_device_credentials set last_used_at = now() where id = %s",
                (identity["credential_id"],),
            )
            cursor.execute(
                """
                select id, display_name, platform, app_version, last_seen_at
                from relay_hosts
                where id = %s and revoked_at is null
                """,
                (identity["host_id"],),
            )
            host = cursor.fetchone()
            if host is None:
                raise AuthenticationFailed
            cursor.execute(
                """
                select schema_version, sampled_at, received_at,
                       five_hour_used, five_hour_reset_at,
                       weekly_used, weekly_reset_at, plan_type,
                       reset_credits_available, credits_balance,
                       spend_control_reached, rate_limit_reached_type,
                       collector_state, collector_message_code
                from relay_quota_state
                where host_id = %s
                """,
                (identity["host_id"],),
            )
            quota = cursor.fetchone()
            return {
                "api_version": 1,
                "host": dict(host),
                "quota": self._json_safe_quota(quota) if quota else None,
            }

    @staticmethod
    def _authenticate_host(cursor, credential_id: UUID, digest: str) -> dict:
        cursor.execute(
            """
            select c.id as credential_id, c.host_id, c.token_digest
            from relay_host_credentials c
            join relay_hosts h on h.id = c.host_id
            where c.id = %s
              and c.revoked_at is null
              and h.revoked_at is null
            for update of c, h
            """,
            (credential_id,),
        )
        identity = cursor.fetchone()
        if identity is None or not hmac.compare_digest(
            identity["token_digest"], digest
        ):
            raise AuthenticationFailed
        return identity

    @staticmethod
    def _authenticate_device(cursor, credential_id: UUID, digest: str) -> dict:
        cursor.execute(
            """
            select c.id as credential_id, c.device_id, d.host_id,
                   c.token_digest
            from relay_device_credentials c
            join relay_devices d on d.id = c.device_id
            join relay_hosts h on h.id = d.host_id
            where c.id = %s
              and c.revoked_at is null
              and d.revoked_at is null
              and h.revoked_at is null
            for update of c, d, h
            """,
            (credential_id,),
        )
        identity = cursor.fetchone()
        if identity is None or not hmac.compare_digest(
            identity["token_digest"], digest
        ):
            raise AuthenticationFailed
        return identity

    @staticmethod
    def _json_safe_quota(quota: dict) -> dict:
        result = dict(quota)
        for field in ("five_hour_used", "weekly_used", "credits_balance"):
            if result[field] is not None:
                result[field] = float(result[field])
        return result
