"""Desktop FastAPI sidecar entry point.

The Tauri parent starts this executable, reads its single readiness line from
stdout, then waits for ``/api/health`` before navigating its webview. The
sidecar owns a socket already bound by the OS, so no fixed desktop port or
check-then-bind race is introduced.
"""

import argparse
import os
import socket
import sys

import uvicorn


READINESS_PREFIX = "CODEX_QUOTA_DESKTOP_PORT="
LOOPBACK_HOST = "127.0.0.1"


def create_loopback_socket(port=0):
    """Allocate a loopback-only listening socket and return it to Uvicorn."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((LOOPBACK_HOST, port))
    listener.listen(socket.SOMAXCONN)
    listener.set_inheritable(True)
    return listener


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the Codex Quota Monitor desktop backend."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Loopback port; 0 asks the OS for an ephemeral port.",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Override the desktop application-data directory.",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
    )
    return parser.parse_args(argv)


def configure_desktop_environment(args):
    os.environ["CODEX_QUOTA_DESKTOP"] = "1"
    os.environ["CODEX_QUOTA_HOST"] = LOOPBACK_HOST

    if args.data_dir:
        os.environ["CODEX_QUOTA_DATA_DIR"] = args.data_dir


def main(argv=None):
    args = parse_args(argv)
    configure_desktop_environment(args)

    # Import only after desktop configuration is in the environment; app.main
    # captures its configuration when imported.
    from app.main import app

    listener = create_loopback_socket(args.port)
    selected_port = listener.getsockname()[1]
    print(f"{READINESS_PREFIX}{selected_port}", flush=True)

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            log_level=args.log_level,
        )
    )

    try:
        server.run(sockets=[listener])
    finally:
        listener.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
