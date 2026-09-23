import argparse
import sys

import uvicorn

from app.adapters.codex_stdio import CodexAppServer
from app.core.quota import normalize_rate_limits
from app.doctor import main as doctor_main


def format_percent_used(value):
    if value is None:
        return "unavailable"

    remaining = max(0, 100 - value)

    return (
        f"{value:g}% used / "
        f"{remaining:g}% remaining"
    )


def status_command():
    client = CodexAppServer()

    try:
        client.start()

        response = client.get_rate_limits()

        quota = normalize_rate_limits(
            response
        )

        print("Codex Quota Monitor")
        print()

        print(
            "5-hour: "
            + format_percent_used(
                quota.get(
                    "five_hour_used"
                )
            )
        )

        print(
            "Weekly:  "
            + format_percent_used(
                quota.get(
                    "weekly_used"
                )
            )
        )

        print(
            "Plan:    "
            + str(
                quota.get(
                    "plan_type"
                )
                or "unknown"
            )
        )

        print(
            "Resets:  "
            + str(
                quota.get(
                    "reset_credits_available",
                    0,
                )
            )
            + " available"
        )

        return 0

    except Exception as exc:
        print(
            f"Unable to read Codex quota: {exc}",
            file=sys.stderr,
        )

        return 1

    finally:
        client.stop()


def serve_command(args):
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )

    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="codex-quota",
        description=(
            "Local-first Codex usage "
            "and quota monitor."
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version="codex-quota-monitor 0.2.0",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "doctor",
        help=(
            "Check whether this machine "
            "can run Codex Quota Monitor."
        ),
    )

    subparsers.add_parser(
        "status",
        help=(
            "Read the current Codex "
            "quota directly."
        ),
    )

    serve_parser = (
        subparsers.add_parser(
            "serve",
            help=(
                "Run the web dashboard."
            ),
        )
    )

    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help=(
            "Address to bind to "
            "(default: 127.0.0.1)."
        ),
    )

    serve_parser.add_argument(
        "--port",
        type=int,
        default=8093,
        help=(
            "TCP port to listen on "
            "(default: 8093)."
        ),
    )

    serve_parser.add_argument(
        "--log-level",
        choices=[
            "critical",
            "error",
            "warning",
            "info",
            "debug",
            "trace",
        ],
        default="info",
    )

    return parser


def main(argv=None):
    parser = build_parser()

    args = parser.parse_args(
        argv
    )

    if args.command == "doctor":
        return doctor_main()

    if args.command == "status":
        return status_command()

    if args.command == "serve":
        return serve_command(args)

    parser.error(
        "Unknown command"
    )

    return 2


if __name__ == "__main__":
    sys.exit(main())
