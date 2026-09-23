import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path


def detect_platform():
    return {
        "system": platform.system().lower(),
        "release": platform.release(),
        "machine": platform.machine().lower(),
        "python": platform.python_version(),
    }


def find_codex():
    configured = os.environ.get("CODEX_BIN")

    if configured:
        path = Path(configured).expanduser()

        if path.is_file():
            return str(path)

    return shutil.which("codex")


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
