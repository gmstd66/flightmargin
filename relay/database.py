"""PostgreSQL operations for the FlightMargin mobile relay."""

from contextlib import contextmanager
import hmac
from typing import Iterator
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from relay.config import RelayConfig
from relay.credentials import ParsedCredential, credential_digest
from relay.models import HostRegistration, QuotaReport


class RegistrationConflict(Exception):
    """The requested host or credential identifier is already in conflicting use."""


class AuthenticationFailed(Exception):
    """The supplied credential is unknown, incorrect, or revoked."""


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
            identity = self._authenticate_host(cursor, credential.credential_id, digest)
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
