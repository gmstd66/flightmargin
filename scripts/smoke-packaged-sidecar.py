#!/usr/bin/env python3
"""Smoke the built desktop sidecar with isolated state and no hosted relay."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
from urllib.request import urlopen


READY = re.compile(r"^CODEX_QUOTA_DESKTOP_PORT=([0-9]{1,5})$")


def stop_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    args = parser.parse_args()
    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error(f"sidecar does not exist: {binary}")

    with tempfile.TemporaryDirectory(prefix="flightmargin-i05b-sidecar-") as temporary:
        environment = os.environ.copy()
        for secret_name in (
            "FLIGHTMARGIN_RELAY_DATABASE_URL",
            "FLIGHTMARGIN_RELAY_PEPPER",
            "SUPABASE_DB_PASSWORD",
            "SUPABASE_PROJECT_REF",
        ):
            environment.pop(secret_name, None)
        environment.update(
            {
                "CODEX_BIN": str(Path(temporary) / "missing-codex"),
                "FLIGHTMARGIN_RELAY_ENDPOINT": "http://127.0.0.1:9",
                "PYTHONUTF8": "1",
            }
        )
        process = subprocess.Popen(
            [str(binary), "--data-dir", temporary, "--log-level", "warning"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
        )
        try:
            assert process.stdout is not None
            deadline = time.monotonic() + 30
            port = None
            lines: queue.Queue[str] = queue.Queue()

            def read_stdout() -> None:
                assert process.stdout is not None
                for output_line in process.stdout:
                    lines.put(output_line)

            threading.Thread(target=read_stdout, daemon=True).start()
            while time.monotonic() < deadline:
                try:
                    line = lines.get(timeout=min(0.25, deadline - time.monotonic())).strip()
                except queue.Empty:
                    if process.poll() is not None:
                        raise RuntimeError("packaged sidecar exited before readiness")
                    continue
                match = READY.fullmatch(line)
                if match:
                    port = int(match.group(1))
                    break
                if process.poll() is not None:
                    raise RuntimeError("packaged sidecar exited before readiness")
            if port is None:
                raise RuntimeError("packaged sidecar did not report readiness")

            base = f"http://127.0.0.1:{port}"
            for path, marker in (
                ("/api/health", b'"status"'),
                ("/", b"FlightMargin"),
                ("/static/qrcode.min.js", b"QRCode"),
            ):
                with urlopen(f"{base}{path}", timeout=10) as response:
                    body = response.read()
                    if response.status != 200 or marker not in body:
                        raise RuntimeError(f"packaged sidecar smoke failed for {path}")
        finally:
            stop_process_tree(process)
    print("Isolated packaged sidecar runtime smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
