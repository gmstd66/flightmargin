import json
import os
import queue
import shutil
import subprocess
import threading
from typing import Any

from app.version import (
    __version__,
)


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
        self.executable = (
            executable
            or os.environ.get("CODEX_BIN")
            or shutil.which("codex")
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
                        "codex-quota-monitor",
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
