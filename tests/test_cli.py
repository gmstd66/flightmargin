from app.cli import (
    build_parser,
    format_percent_used,
)

from app.version import (
    __version__,
)


def test_format_percent_used():
    assert (
        format_percent_used(26)
        == "26% used / 74% remaining"
    )


def test_format_percent_used_float():
    assert (
        format_percent_used(26.5)
        == (
            "26.5% used / "
            "73.5% remaining"
        )
    )


def test_format_percent_used_missing():
    assert (
        format_percent_used(None)
        == "unavailable"
    )


def test_status_command_parses():
    parser = build_parser()

    args = parser.parse_args(
        ["status"]
    )

    assert (
        args.command
        == "status"
    )


def test_doctor_command_parses():
    parser = build_parser()

    args = parser.parse_args(
        ["doctor"]
    )

    assert (
        args.command
        == "doctor"
    )


def test_version_uses_canonical_application_version(
    capsys,
):
    parser = build_parser()

    try:
        parser.parse_args(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("--version did not exit")

    assert (
        capsys.readouterr().out
        == f"codex-quota-monitor {__version__}\n"
    )


def test_serve_defaults():
    parser = build_parser()

    args = parser.parse_args(
        ["serve"]
    )

    assert (
        args.command
        == "serve"
    )

    assert (
        args.host
        == "127.0.0.1"
    )

    assert (
        args.port
        == 8093
    )

    assert (
        args.log_level
        == "info"
    )


def test_serve_custom_address():
    parser = build_parser()

    args = parser.parse_args(
        [
            "serve",
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
            "--log-level",
            "debug",
        ]
    )

    assert (
        args.host
        == "0.0.0.0"
    )

    assert (
        args.port
        == 9000
    )

    assert (
        args.log_level
        == "debug"
    )


def test_service_unit_parses():
    parser = build_parser()

    args = parser.parse_args(
        [
            "service-unit",
            "--user",
            "quotauser",
        ]
    )

    assert (
        args.command
        == "service-unit"
    )

    assert (
        args.user
        == "quotauser"
    )


def test_service_unit_cli_executable():
    parser = build_parser()

    args = parser.parse_args(
        [
            "service-unit",
            "--cli-executable",
            (
                "/opt/codex-quota/"
                "venv/bin/codex-quota"
            ),
        ]
    )

    assert (
        args.cli_executable
        == (
            "/opt/codex-quota/"
            "venv/bin/codex-quota"
        )
    )
