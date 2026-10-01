"""Stable host identity creation and platform-specific credential storage."""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import json
import os
from pathlib import Path
import platform
import re
import secrets
from uuid import UUID, uuid4


IDENTITY_FILE = "mobile-relay-host.json"
_CREDENTIAL_PATTERN = re.compile(
    r"^fmh1\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    r"\.[A-Za-z0-9_-]{43}$"
)


class IdentityStorageError(RuntimeError):
    """Raised without secret material when stored host identity is unusable."""


@dataclass(frozen=True)
class HostIdentity:
    host_id: str
    credential: str

    def validate(self) -> "HostIdentity":
        try:
            UUID(self.host_id)
        except (ValueError, TypeError, AttributeError):
            raise IdentityStorageError("Stored relay host identity is invalid") from None
        if not isinstance(self.credential, str) or not _CREDENTIAL_PATTERN.fullmatch(
            self.credential
        ):
            raise IdentityStorageError("Stored relay host identity is invalid")
        try:
            encoded = self.credential.rsplit(".", 1)[1]
            decoded = base64.urlsafe_b64decode(encoded + "=")
            canonical = base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii")
        except (ValueError, TypeError):
            raise IdentityStorageError("Stored relay host identity is invalid") from None
        if len(decoded) != 32 or not secrets.compare_digest(canonical, encoded):
            raise IdentityStorageError("Stored relay host identity is invalid")
        return self


class CredentialProtector:
    def protect(self, plaintext: bytes) -> bytes:
        raise NotImplementedError

    def unprotect(self, protected: bytes) -> bytes:
        raise NotImplementedError


class WindowsDPAPIProtector(CredentialProtector):
    """Protect bytes for the current Windows user using CryptProtectData."""

    UI_FORBIDDEN = 0x01

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

    @staticmethod
    def _blob(value: bytes):
        buffer = ctypes.create_string_buffer(value)
        blob = WindowsDPAPIProtector.DATA_BLOB(
            len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
        )
        return buffer, blob

    def _transform(self, value: bytes, *, protect: bool) -> bytes:
        if platform.system().lower() != "windows" or not hasattr(ctypes, "windll"):
            raise IdentityStorageError("Windows credential protection is unavailable")
        buffer, source = self._blob(value)
        destination = self.DATA_BLOB()
        try:
            if protect:
                success = ctypes.windll.crypt32.CryptProtectData(
                    ctypes.byref(source),
                    "FlightMargin Mobile Relay",
                    None,
                    None,
                    None,
                    self.UI_FORBIDDEN,
                    ctypes.byref(destination),
                )
            else:
                success = ctypes.windll.crypt32.CryptUnprotectData(
                    ctypes.byref(source),
                    None,
                    None,
                    None,
                    None,
                    self.UI_FORBIDDEN,
                    ctypes.byref(destination),
                )
            if not success:
                raise IdentityStorageError("Windows credential protection failed")
            return ctypes.string_at(destination.pbData, destination.cbData)
        finally:
            if destination.pbData:
                ctypes.windll.kernel32.LocalFree(destination.pbData)
            del buffer

    def protect(self, plaintext: bytes) -> bytes:
        return self._transform(plaintext, protect=True)

    def unprotect(self, protected: bytes) -> bytes:
        return self._transform(protected, protect=False)


def generate_identity() -> HostIdentity:
    secret = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")
    return HostIdentity(
        host_id=str(uuid4()),
        credential=f"fmh1.{uuid4()}.{secret}",
    )


class HostIdentityStore:
    def __init__(
        self,
        data_dir: Path,
        *,
        system: str | None = None,
        protector: CredentialProtector | None = None,
    ):
        self.path = Path(data_dir) / IDENTITY_FILE
        self.system = (system or platform.system()).lower()
        self.protector = protector or (
            WindowsDPAPIProtector() if self.system == "windows" else None
        )

    def load(self) -> HostIdentity | None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError, TypeError):
            raise IdentityStorageError("Stored relay host identity is invalid") from None
        try:
            host_id = raw["host_id"]
            if raw.get("schema_version") != 1:
                raise KeyError("schema_version")
            if self.system == "windows":
                protected = base64.b64decode(raw["protected_credential"], validate=True)
                assert self.protector is not None
                credential = self.protector.unprotect(protected).decode("utf-8")
            else:
                credential = raw["credential"]
        except (KeyError, ValueError, TypeError, UnicodeError, IdentityStorageError):
            raise IdentityStorageError("Stored relay host identity is invalid") from None
        return HostIdentity(host_id=host_id, credential=credential).validate()

    def load_or_create(self) -> HostIdentity:
        existing = self.load()
        if existing is not None:
            return existing
        identity = generate_identity()
        self._save(identity)
        return identity

    def _save(self, identity: HostIdentity) -> None:
        identity.validate()
        existed = self.path.parent.exists()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not existed and self.system != "windows":
            os.chmod(self.path.parent, 0o700)
        if self.system == "windows":
            assert self.protector is not None
            protected = self.protector.protect(identity.credential.encode("utf-8"))
            payload = {
                "schema_version": 1,
                "host_id": identity.host_id,
                "protected_credential": base64.b64encode(protected).decode("ascii"),
            }
        else:
            payload = {
                "schema_version": 1,
                "host_id": identity.host_id,
                "credential": identity.credential,
            }
        temporary = self.path.with_suffix(".tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.write("\n")
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        os.chmod(temporary, 0o600)
        temporary.replace(self.path)
        if self.system != "windows":
            os.chmod(self.path, 0o600)
