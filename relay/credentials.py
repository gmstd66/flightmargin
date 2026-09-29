"""Parsing and one-way hashing for FlightMargin relay credentials."""

from dataclasses import dataclass
import base64
import hashlib
import hmac
import re
from uuid import UUID


_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_SECRET = r"[A-Za-z0-9_-]{43}"
_CREDENTIAL = re.compile(
    rf"^(?P<prefix>fmh1|fmd1)\.(?P<credential_id>{_UUID})\.(?P<secret>{_SECRET})$"
)
_KINDS = {"host": "fmh1", "device": "fmd1"}
CREDENTIAL_MAX_LENGTH = 128


class InvalidCredential(ValueError):
    """Raised when a FlightMargin credential is malformed or has the wrong kind."""


@dataclass(frozen=True)
class ParsedCredential:
    kind: str
    credential_id: UUID
    secret: str


def parse_credential(value: str, expected_kind: str) -> ParsedCredential:
    prefix = _KINDS.get(expected_kind)
    if prefix is None:
        raise ValueError("Unsupported credential kind")
    if not isinstance(value, str):
        raise InvalidCredential("Malformed credential")

    match = _CREDENTIAL.fullmatch(value)
    if match is None or match.group("prefix") != prefix:
        raise InvalidCredential("Malformed credential")

    secret = match.group("secret")
    try:
        decoded = base64.urlsafe_b64decode(secret + "=")
    except (ValueError, TypeError):
        raise InvalidCredential("Malformed credential") from None
    canonical = base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii")
    if len(decoded) != 32 or not hmac.compare_digest(canonical, secret):
        raise InvalidCredential("Malformed credential")

    return ParsedCredential(
        kind=expected_kind,
        credential_id=UUID(match.group("credential_id")),
        secret=secret,
    )


def credential_digest(credential: ParsedCredential, pepper: bytes) -> str:
    context = (
        f"{credential.kind}:{credential.credential_id}:{credential.secret}"
    ).encode("ascii")
    return hmac.new(pepper, context, hashlib.sha256).hexdigest()
