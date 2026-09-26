from app.about import (
    APP_NAME,
    build_about_payload,
    parse_codex_cli_version,
)
from app.version import __version__


def build_windows_payload(codex_cli_version="0.156.1"):
    return build_about_payload(
        app_version=__version__,
        codex_cli_version=codex_cli_version,
        data_directory="C:/Users/private-name/AppData/Local/Codex Quota Monitor",
        log_directory="C:/Users/private-name/AppData/Local/Codex Quota Monitor/logs",
        system="Windows",
        release="11",
        machine="AMD64",
        environ={"LOCALAPPDATA": "C:/Users/private-name/AppData/Local"},
    )


def test_about_uses_canonical_version_and_safe_windows_paths():
    payload = build_windows_payload()

    assert payload["app_name"] == APP_NAME
    assert payload["app_version"] == __version__
    assert payload["data_directory"] == "%LOCALAPPDATA%\\Codex Quota Monitor"
    assert payload["log_directory"] == "%LOCALAPPDATA%\\Codex Quota Monitor\\logs"
    assert payload["operating_system"] == "Windows 11"
    assert payload["architecture"] == "x64"


def test_codex_cli_version_parser_and_unavailable_state():
    assert parse_codex_cli_version("codex-cli 0.156.1") == "0.156.1"
    assert parse_codex_cli_version(None) is None

    payload = build_windows_payload(codex_cli_version=None)
    assert payload["codex_cli_version"] is None
    assert "Codex CLI: Not detected" in payload["diagnostics"]


def test_copy_diagnostics_is_allowlisted_and_excludes_sensitive_values():
    diagnostics = build_windows_payload()["diagnostics"]

    assert diagnostics == "\n".join(
        (
            "Codex Quota Monitor",
            f"App version: {__version__}",
            "Status: Beta",
            "Codex CLI: 0.156.1",
            "OS: Windows 11 x64",
            "Data directory: %LOCALAPPDATA%\\Codex Quota Monitor",
            "Log directory: %LOCALAPPDATA%\\Codex Quota Monitor\\logs",
        )
    )
    for sensitive_text in (
        "private-name",
        "auth.json",
        "token",
        "email",
        "remaining percentage",
        "account identity",
    ):
        assert sensitive_text.lower() not in diagnostics.lower()


def test_linux_about_paths_do_not_expose_home_directory_identity():
    payload = build_about_payload(
        app_version=__version__,
        codex_cli_version=None,
        data_directory="/home/private-name/.local/share/codex-quota-monitor",
        log_directory="systemd journal or process output",
        system="Linux",
        release="6.8.0",
        machine="x86_64",
        environ={"HOME": "/home/private-name"},
    )

    assert payload["data_directory"] == "~/.local/share/codex-quota-monitor"
    assert payload["log_directory"] == "systemd journal or process output"
    assert "private-name" not in payload["diagnostics"]
    assert payload["operating_system"] == "Linux 6.8.0"
