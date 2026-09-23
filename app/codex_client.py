import json
import queue
import subprocess
import threading
from typing import Any


class CodexClient:
    def __init__(self):
        self.process = None
        self.reader_thread = None
        self.pending = {}
        self.next_id = 1
        self.lock = threading.Lock()
        self.request_lock = threading.Lock()

    def start(self):
        if self.process and self.process.poll() is None:
            return

        self.process = subprocess.Popen(
            ["codex", "app-server", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            bufsize=1,
        )

        self.reader_thread = threading.Thread(
            target=self._reader_loop,
            daemon=True,
        )
        self.reader_thread.start()

        result = self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "codex-quota",
                    "version": "0.1.0",
                }
            },
        )

        if not result:
            raise RuntimeError("Codex app-server initialization failed")

    def _reader_loop(self):
        try:
            for line in self.process.stdout:
                line = line.strip()

                if not line:
                    continue

                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue

                request_id = message.get("id")

                if request_id is not None:
                    with self.lock:
                        response_queue = self.pending.get(request_id)

                    if response_queue:
                        response_queue.put(message)

        finally:
            with self.lock:
                for response_queue in self.pending.values():
                    response_queue.put(
                        {
                            "error": {
                                "message": "Codex app-server exited"
                            }
                        }
                    )

    def request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        timeout: float = 15.0,
    ):
        if not self.process or self.process.poll() is not None:
            if method != "initialize":
                self.start()

        with self.lock:
            request_id = self.next_id
            self.next_id += 1

            response_queue = queue.Queue(maxsize=1)
            self.pending[request_id] = response_queue

        payload = {
            "method": method,
            "id": request_id,
        }

        if params is not None:
            payload["params"] = params

        try:
            self.process.stdin.write(
                json.dumps(payload) + "\n"
            )
            self.process.stdin.flush()

            response = response_queue.get(
                timeout=timeout
            )

            if "error" in response:
                raise RuntimeError(
                    response["error"].get(
                        "message",
                        str(response["error"]),
                    )
                )

            return response.get("result")

        finally:
            with self.lock:
                self.pending.pop(
                    request_id,
                    None,
                )

    def get_rate_limits(self):
        with self.request_lock:
            result = self.request(
                "account/rateLimits/read"
            )

        limits_by_id = (
            result.get("rateLimitsByLimitId")
            or {}
        )

        if "codex" in limits_by_id:
            limits = limits_by_id["codex"]
        else:
            limits = result.get("rateLimits")

        if not limits:
            raise RuntimeError(
                "Codex rate-limit data missing from response"
            )

        return {
            "limits": limits,
            "reset_credits": (
                result.get("rateLimitResetCredits")
                or {}
            ),
        }

    def stop(self):
        if not self.process:
            return

        if self.process.poll() is None:
            self.process.terminate()

            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()

        self.process = None
