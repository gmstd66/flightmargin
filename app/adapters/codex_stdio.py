import json
import os
import queue
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

from app.version import (
    __version__,
)


def windows_hidden_subprocess_kwargs(system_name=None):
    """Prevent desktop-invoked Windows CLI wrappers from allocating a console."""
    if (system_name or os.name) != "nt":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return {
        "creationflags": subprocess.CREATE_NO_WINDOW,
        "startupinfo": startupinfo,
    }


def resolve_windows_npm_codex(
    executable,
    system_name=None,
    machine=None,
):
    """Resolve an official npm shim to its packaged native Codex binary.

    The npm shim otherwise leaves cmd.exe, conhost.exe, and Node resident for
    the lifetime of the app-server. Only recognized official package layouts
    are optimized; every other installation keeps using its original command.
    """
    if not executable or (system_name or os.name) != "nt":
        return executable

    wrapper = Path(executable)
    if wrapper.name.lower() not in {"codex", "codex.cmd"}:
        return executable

    package_root = wrapper.parent / "node_modules" / "@openai" / "codex"
    if not (package_root / "bin" / "codex.js").is_file():
        return executable

    machine = (machine or os.environ.get("PROCESSOR_ARCHITECTURE", "")).lower()
    targets = {
        "amd64": ("codex-win32-x64", "x86_64-pc-windows-msvc"),
        "x86_64": ("codex-win32-x64", "x86_64-pc-windows-msvc"),
        "arm64": ("codex-win32-arm64", "aarch64-pc-windows-msvc"),
        "aarch64": ("codex-win32-arm64", "aarch64-pc-windows-msvc"),
    }
    target = targets.get(machine)
    if not target:
        return executable

    package_name, triple = target
    package_parents = (
        package_root / "node_modules" / "@openai",
        wrapper.parent / "node_modules" / "@openai",
    )
    for parent in package_parents:
        native = parent / package_name / "vendor" / triple / "bin" / "codex.exe"
        if native.is_file():
            return str(native)

    return executable


class CodexNotFoundError(RuntimeError):
    pass


class CodexAppServer:
    """
    Adapter for:

        codex app-server --stdio

    The rest of the application does not need to know
    how the Codex subprocess is launched or communicated
    with.
    """

    def __init__(
        self,
        executable: str | None = None,
    ):
        configured = executable or os.environ.get("CODEX_BIN")
        discovered = configured or shutil.which("codex")
        self.executable = (
            discovered
            if configured
            else resolve_windows_npm_codex(discovered)
        )

        self.process = None
        self.reader_thread = None

        self.pending = {}
        self.next_id = 1

        self.pending_lock = threading.Lock()
        self.request_lock = threading.Lock()


    def _check_executable(self):
        if not self.executable:
            raise CodexNotFoundError(
                "Codex CLI was not found. "
                "Install Codex or set CODEX_BIN."
            )


    def start(self):
        if (
            self.process
            and self.process.poll() is None
        ):
            return

        self._check_executable()

        self.process = subprocess.Popen(
            [
                self.executable,
                "app-server",
                "--stdio",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            bufsize=1,
            **windows_hidden_subprocess_kwargs(),
        )

        self.reader_thread = (
            threading.Thread(
                target=self._reader_loop,
                daemon=True,
            )
        )

        self.reader_thread.start()

        result = self.request(
            "initialize",
            {
                "clientInfo": {
                    "name":
                        "flightmargin",
                    "version":
                        __version__,
                }
            },
        )

        if not result:
            raise RuntimeError(
                "Codex app-server "
                "initialization failed"
            )


    def _reader_loop(self):
        try:
            for line in self.process.stdout:
                line = line.strip()

                if not line:
                    continue

                try:
                    message = json.loads(
                        line
                    )
                except json.JSONDecodeError:
                    continue

                request_id = (
                    message.get("id")
                )

                if request_id is None:
                    continue

                with self.pending_lock:
                    response_queue = (
                        self.pending.get(
                            request_id
                        )
                    )

                if response_queue:
                    response_queue.put(
                        message
                    )

        finally:
            with self.pending_lock:
                queues = list(
                    self.pending.values()
                )

            for response_queue in queues:
                try:
                    response_queue.put_nowait(
                        {
                            "error": {
                                "message":
                                    "Codex app-server exited"
                            }
                        }
                    )
                except queue.Full:
                    pass


    def request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        timeout: float = 15.0,
    ):
        if (
            not self.process
            or self.process.poll()
            is not None
        ):
            if method != "initialize":
                self.start()

        with self.pending_lock:
            request_id = self.next_id
            self.next_id += 1

            response_queue = queue.Queue(
                maxsize=1
            )

            self.pending[
                request_id
            ] = response_queue

        payload = {
            "method": method,
            "id": request_id,
        }

        if params is not None:
            payload["params"] = params

        try:
            if (
                not self.process
                or not self.process.stdin
            ):
                raise RuntimeError(
                    "Codex app-server "
                    "stdin unavailable"
                )

            self.process.stdin.write(
                json.dumps(payload)
                + "\n"
            )

            self.process.stdin.flush()

            response = (
                response_queue.get(
                    timeout=timeout
                )
            )

            if "error" in response:
                error = response["error"]

                if isinstance(
                    error,
                    dict,
                ):
                    message = (
                        error.get(
                            "message",
                            str(error),
                        )
                    )
                else:
                    message = str(error)

                raise RuntimeError(
                    message
                )

            return response.get(
                "result"
            )

        finally:
            with self.pending_lock:
                self.pending.pop(
                    request_id,
                    None,
                )


    def get_rate_limits(self):
        with self.request_lock:
            return self.request(
                "account/rateLimits/read"
            )


    def stop(self):
        process = self.process

        if not process:
            return

        if process.poll() is None:
            process.terminate()

            try:
                process.wait(
                    timeout=3
                )
            except subprocess.TimeoutExpired:
                process.kill()

        self.process = None
