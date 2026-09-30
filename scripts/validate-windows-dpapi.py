#!/usr/bin/env python3
"""Exercise the real current-user Windows DPAPI host identity path."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.mobile_relay.identity import HostIdentityStore, IdentityStorageError


def credential_digest(credential: str) -> str:
    return hashlib.sha256(credential.encode("utf-8")).hexdigest()


def child_verify(data_dir: Path, host_id: str, expected_digest: str) -> int:
    identity = HostIdentityStore(data_dir).load_or_create()
    if identity.host_id != host_id:
        raise RuntimeError("host identity changed across processes")
    if credential_digest(identity.credential) != expected_digest:
        raise RuntimeError("host credential changed across processes")
    return 0


def child_expect_failure(data_dir: Path) -> int:
    try:
        HostIdentityStore(data_dir).load()
    except IdentityStorageError:
        return 0
    raise RuntimeError("tampered DPAPI data did not fail closed")


def corrupt_protected_credential(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    protected = bytearray(base64.b64decode(payload["protected_credential"], validate=True))
    if not protected:
        raise RuntimeError("DPAPI returned an empty protected credential")
    protected[len(protected) // 2] ^= 0x01
    payload["protected_credential"] = base64.b64encode(protected).decode("ascii")
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def run_native_validation() -> int:
    if platform.system().lower() != "windows":
        raise RuntimeError("native DPAPI validation must run on Windows")
    script = Path(__file__).resolve()
    with tempfile.TemporaryDirectory(prefix="flightmargin-i05b-dpapi-") as temporary:
        data_dir = Path(temporary)
        identity = HostIdentityStore(data_dir).load_or_create()
        identity_path = HostIdentityStore(data_dir).path
        stored = identity_path.read_text(encoding="utf-8")
        if identity.credential in stored or "\"credential\"" in stored:
            raise RuntimeError("plaintext credential was written to host identity storage")
        if "protected_credential" not in json.loads(stored):
            raise RuntimeError("host identity storage has no DPAPI-protected credential")

        subprocess.run(
            [
                sys.executable,
                str(script),
                "--child-verify",
                str(data_dir),
                identity.host_id,
                credential_digest(identity.credential),
            ],
            check=True,
        )
        corrupt_protected_credential(identity_path)
        subprocess.run(
            [sys.executable, str(script), "--child-expect-failure", str(data_dir)],
            check=True,
        )
    print("Native Windows DPAPI host identity validation: PASS")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--child-verify", nargs=3, metavar=("DATA_DIR", "HOST_ID", "DIGEST"))
    group.add_argument("--child-expect-failure", metavar="DATA_DIR")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.child_verify:
        data_dir, host_id, digest = args.child_verify
        return child_verify(Path(data_dir), host_id, digest)
    if args.child_expect_failure:
        return child_expect_failure(Path(args.child_expect_failure))
    return run_native_validation()


if __name__ == "__main__":
    raise SystemExit(main())
