import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.adapters.codex_stdio import windows_hidden_subprocess_kwargs


def detect_platform():
    return {
        "system": platform.system().lower(),
        "release": platform.release(),
        "machine": platform.machine().lower(),
        "python": platform.python_version(),
    }


def codex_candidate_paths(
    system=None,
    environ=None,
):
    """Return documented platform-specific fallback paths for Codex.

    PATH remains the primary discovery mechanism. These are deliberately small
    fallbacks for the standalone installer, not a search of arbitrary user
    directories or an attempt to locate credentials.
    """
    environ = os.environ if environ is None else environ
    system = (system or platform.system()).lower()

    if system == "windows":
        local_app_data = environ.get("LOCALAPPDATA")
        if local_app_data:
            return [
                Path(local_app_data)
                / "Programs"
                / "OpenAI"
                / "Codex"
                / "bin"
                / "codex.exe"
            ]
        return []

    if system in {"darwin", "linux"}:
        return [Path.home() / ".local" / "bin" / "codex"]

    return []


def find_codex(
    system=None,
    environ=None,
    which=None,
):
    environ = os.environ if environ is None else environ
    which = shutil.which if which is None else which
    configured = environ.get("CODEX_BIN")

    if configured:
        path = Path(configured).expanduser()

        if path.is_file():
            return str(path)

    executable_names = ["codex"]

    if (system or platform.system()).lower() == "windows":
        executable_names.append("codex.exe")

    for executable_name in executable_names:
        found = which(executable_name)
        if found:
            return found

    for candidate in codex_candidate_paths(
        system=system,
        environ=environ,
    ):
        if candidate.is_file():
            return str(candidate)

    return None


def get_codex_version(executable=None):
    executable = executable or find_codex()

    if not executable:
        return None

    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            **windows_hidden_subprocess_kwargs(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    return result.stdout.strip() or result.stderr.strip() or None


def check_directory_writable(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)

    try:
        with tempfile.NamedTemporaryFile(
            dir=path,
            prefix=".codex-quota-write-test-",
            delete=True,
        ):
            pass
    except OSError:
        return False

    return True
