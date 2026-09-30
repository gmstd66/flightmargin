#!/usr/bin/env python3
"""Validate hosted public relay limits and remove only test-created buckets."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


RELAY_URL = "https://samcdyrwfwrlxzypzgmj.supabase.co/functions/v1/relay-v1"
DATABASE_ENV = "FLIGHTMARGIN_RELAY_DATABASE_URL"
INVALID_PAYLOAD = json.dumps({"i05b_validation": True}).encode("utf-8")


@dataclass(frozen=True)
class BucketKey:
    action: str
    identity_digest: str
    window_started_at: datetime


class ValidationError(RuntimeError):
    """Expected validation failure whose message contains no secret material."""


def request_status(
    request: Request,
    *,
    opener: Callable[..., Any] = urlopen,
) -> tuple[int, Any]:
    """Return status and headers without including request/response secrets."""
    try:
        response = opener(request, timeout=15)
    except HTTPError as error:
        error.read()
        return error.code, error.headers
    with response:
        response.read()
        return response.status, response.headers


def post_invalid(path: str, *, opener: Callable[..., Any] = urlopen) -> tuple[int, Any]:
    return request_status(
        Request(
            f"{RELAY_URL}{path}",
            data=INVALID_PAYLOAD,
            method="POST",
            headers={"Content-Type": "application/json"},
        ),
        opener=opener,
    )


def validate_limit(
    name: str,
    path: str,
    allowed_count: int,
    *,
    opener: Callable[..., Any] = urlopen,
) -> None:
    for request_number in range(1, allowed_count + 1):
        status, _headers = post_invalid(path, opener=opener)
        if status != 422:
            raise ValidationError(
                f"{name} request {request_number} reached unexpected status {status}; "
                "expected validation status 422"
            )
    status, headers = post_invalid(path, opener=opener)
    if status != 429:
        raise ValidationError(f"{name} threshold returned {status}; expected 429")
    retry_after = headers.get("Retry-After")
    try:
        valid_retry_after = int(retry_after) > 0
    except (TypeError, ValueError):
        valid_retry_after = False
    if not valid_retry_after:
        raise ValidationError(
            f"{name} 429 response is missing a valid Retry-After header"
        )


def validate_hosted_relay(*, opener: Callable[..., Any] = urlopen) -> None:
    status, _headers = request_status(Request(f"{RELAY_URL}/health"), opener=opener)
    if status != 200:
        raise ValidationError(f"hosted relay health returned {status}; expected 200")
    print("Hosted relay health: PASS")

    validate_limit("host-registration", "/v1/hosts/register", 10, opener=opener)
    print("Host-registration public limit: PASS")
    validate_limit("pairing-claim", "/v1/pairings/claim", 20, opener=opener)
    print("Pairing-claim public limit: PASS")


def snapshot_bucket_keys(connection: Any) -> set[BucketKey]:
    with connection.cursor() as cursor:
        cursor.execute(
            """select action, identity_digest, window_started_at
               from public.relay_rate_limit_buckets"""
        )
        return {BucketKey(*row) for row in cursor.fetchall()}


def delete_bucket_keys(connection: Any, keys: set[BucketKey]) -> None:
    if not keys:
        return
    parameters = [
        (key.action, key.identity_digest, key.window_started_at)
        for key in sorted(
            keys,
            key=lambda key: (key.action, key.identity_digest, key.window_started_at),
        )
    ]
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.executemany(
                """delete from public.relay_rate_limit_buckets
                   where action = %s
                     and identity_digest = %s
                     and window_started_at = %s""",
                parameters,
            )


def validate_with_cleanup(connection: Any, validator: Callable[[], None]) -> None:
    before = snapshot_bucket_keys(connection)
    try:
        validator()
    finally:
        after = snapshot_bucket_keys(connection)
        created = after - before
        delete_bucket_keys(connection, created)
        print(f"Removed {len(created)} newly created rate-limit bucket(s)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-hosted",
        action="store_true",
        help="confirm that this explicitly authorized run may contact hosted Supabase",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.confirm_hosted:
        print("ERROR: hosted validation requires --confirm-hosted", file=sys.stderr)
        return 2
    database_url = os.environ.get(DATABASE_ENV)
    if not database_url:
        print(f"ERROR: required secret {DATABASE_ENV} is not configured", file=sys.stderr)
        return 2
    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg is required for hosted validation", file=sys.stderr)
        return 2

    try:
        with psycopg.connect(
            database_url,
            connect_timeout=15,
            autocommit=True,
        ) as connection:
            validate_with_cleanup(connection, validate_hosted_relay)
    except ValidationError as error:
        print(f"ERROR: hosted relay validation failed: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(
            "ERROR: hosted relay validation failed during database or network "
            f"operation ({type(error).__name__})",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
