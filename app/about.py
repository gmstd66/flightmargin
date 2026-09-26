"""Safe, local-only metadata for the desktop About page."""

import os
import platform
import re
from functools import lru_cache
from pathlib import Path, PurePosixPath, PureWindowsPath

from app.core.environment import get_codex_version


APP_NAME = "FlightMargin"
APP_STATUS = "Beta"
COPYRIGHT_YEAR = 2026
COPYRIGHT_OWNER = "Guy Champin"


def parse_codex_cli_version(output):
    """Extract the version number from the Codex CLI version response."""
    if not output:
        return None

    match = re.search(
        r"\b\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?\b",
        output,
    )
    return match.group(0) if match else output.strip() or None


@lru_cache(maxsize=4)
def detected_codex_cli_version(executable):
    """Read the already-discovered CLI version once per executable."""
    return parse_codex_cli_version(get_codex_version(executable))


def friendly_path(path, *, system=None, environ=None):
    """Return a diagnostic path without exposing the Windows account name."""
    path = Path(path)
    system = (system or platform.system()).lower()
    environ = os.environ if environ is None else environ

    if system == "windows" and environ.get("LOCALAPPDATA"):
        local_app_data = Path(environ["LOCALAPPDATA"])
        try:
            relative = path.resolve().relative_to(local_app_data.resolve())
        except (OSError, ValueError):
            pass
        else:
            return str(PureWindowsPath("%LOCALAPPDATA%") / relative)

    if system == "linux":
        xdg_data_home = environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            try:
                relative = path.resolve().relative_to(Path(xdg_data_home).resolve())
            except (OSError, ValueError):
                pass
            else:
                return str(
                    PurePosixPath("$XDG_DATA_HOME")
                    / PurePosixPath(relative.as_posix())
                )

        home = environ.get("HOME")
        if home:
            try:
                relative = path.resolve().relative_to(Path(home).resolve())
            except (OSError, ValueError):
                pass
            else:
                return str(
                    PurePosixPath("~")
                    / PurePosixPath(relative.as_posix())
                )

    return str(path)


def friendly_architecture(machine=None):
    machine = (machine or platform.machine()).lower()
    return {
        "amd64": "x64",
        "x86_64": "x64",
        "aarch64": "ARM64",
        "arm64": "ARM64",
    }.get(machine, machine or "unknown")


def build_about_payload(
    *,
    app_version,
    codex_cli_version,
    data_directory,
    log_directory,
    system=None,
    release=None,
    machine=None,
    environ=None,
):
    """Build the allowlisted metadata and copy-safe diagnostic block."""
    system = system or platform.system()
    release = release or platform.release()
    architecture = friendly_architecture(machine)
    operating_system = " ".join(part for part in (system, release) if part)
    data_path = friendly_path(
        data_directory,
        system=system,
        environ=environ,
    )
    log_path = friendly_path(
        log_directory,
        system=system,
        environ=environ,
    )
    cli_display = codex_cli_version or "Not detected"

    diagnostics = "\n".join(
        (
            APP_NAME,
            f"App version: {app_version}",
            f"Status: {APP_STATUS}",
            f"Codex CLI: {cli_display}",
            f"OS: {operating_system} {architecture}",
            f"Data directory: {data_path}",
            f"Log directory: {log_path}",
        )
    )

    return {
        "app_name": APP_NAME,
        "app_version": app_version,
        "status": APP_STATUS,
        "codex_cli_version": codex_cli_version,
        "operating_system": operating_system,
        "architecture": architecture,
        "data_directory": data_path,
        "log_directory": log_path,
        "copyright_year": COPYRIGHT_YEAR,
        "copyright_owner": COPYRIGHT_OWNER,
        "diagnostics": diagnostics,
    }
