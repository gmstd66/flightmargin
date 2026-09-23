import argparse
import getpass
import sys
from pathlib import Path

import uvicorn

from app.adapters.codex_stdio import (
    CodexAppServer,
)

from app.core.config import (
    load_config,
)

from app.core.quota import (
    normalize_rate_limits,
)

from app.doctor import (
    main as doctor_main,
)

from app.systemd import (
    render_systemd_unit,
)


def format_percent_used(value):
    if value is None:
        return "unavailable"

    remaining = max(
        0,
        100 - value,
    )

    return (
        f"{value:g}% used / "
        f"{remaining:g}% remaining"
    )


def status_command():
    config = load_config()

    client = CodexAppServer(
        executable=config.codex_bin
    )

    try:
        client.start()

        response = (
            client.get_rate_limits()
        )

        quota = (
            normalize_rate_limits(
                response
            )
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
            "Unable to read Codex quota: "
            f"{exc}",
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


def service_unit_command(args):
    config = load_config()

    unit = render_systemd_unit(
        config,
        user=args.user,
        group=args.group,
        home=args.home,
        python_executable=(
            args.python_executable
        ),
        codex_executable=(
            args.codex_executable
        ),
    )

    print(
        unit,
        end="",
    )

    return 0


def build_parser():
    config = load_config()

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
        version=(
            "codex-quota-monitor "
            "0.2.0"
        ),
    )

    subparsers = (
        parser.add_subparsers(
            dest="command",
            required=True,
        )
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
        default=config.host,
        help=(
            "Address to bind to "
            f"(default: {config.host})."
        ),
    )

    serve_parser.add_argument(
        "--port",
        type=int,
        default=config.port,
        help=(
            "TCP port to listen on "
            f"(default: {config.port})."
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

    service_parser = (
        subparsers.add_parser(
            "service-unit",
            help=(
                "Generate a systemd "
                "service unit."
            ),
        )
    )

    service_parser.add_argument(
        "--user",
        default=getpass.getuser(),
        help=(
            "System user that will run "
            "the service."
        ),
    )

    service_parser.add_argument(
        "--group",
        default=None,
        help=(
            "System group. Defaults "
            "to the service user."
        ),
    )

    service_parser.add_argument(
        "--home",
        default=str(
            Path.home()
        ),
        help=(
            "HOME directory exposed "
            "to Codex."
        ),
    )

    service_parser.add_argument(
        "--python-executable",
        default=sys.executable,
        help=(
            "Python executable used "
            "by systemd."
        ),
    )

    service_parser.add_argument(
        "--codex-executable",
        default=None,
        help=(
            "Explicit Codex CLI "
            "executable."
        ),
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
        return serve_command(
            args
        )

    if (
        args.command
        == "service-unit"
    ):
        return service_unit_command(
            args
        )

    parser.error(
        "Unknown command"
    )

    return 2


if __name__ == "__main__":
    sys.exit(main())
