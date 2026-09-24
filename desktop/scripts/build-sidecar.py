#!/usr/bin/env python3
"""Build the platform-native desktop FastAPI sidecar with PyInstaller."""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DESKTOP_ROOT = PROJECT_ROOT / "desktop"
BINARY_DIR = DESKTOP_ROOT / "src-tauri" / "binaries"
BUILD_ROOT = DESKTOP_ROOT / ".build" / "pyinstaller"


def default_target():
    machine = platform.machine().lower()
    if sys.platform == "win32":
        return "aarch64-pc-windows-msvc" if "arm" in machine else "x86_64-pc-windows-msvc"
    if sys.platform == "darwin":
        return "aarch64-apple-darwin" if "arm" in machine else "x86_64-apple-darwin"
    return "aarch64-unknown-linux-gnu" if "aarch64" in machine else "x86_64-unknown-linux-gnu"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default=default_target())
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "PyInstaller is required in the build environment. Install it with "
            f"{sys.executable} -m pip install pyinstaller"
        ) from exc

    if BUILD_ROOT.exists():
        shutil.rmtree(BUILD_ROOT)
    BUILD_ROOT.mkdir(parents=True)
    BINARY_DIR.mkdir(parents=True, exist_ok=True)

    executable_suffix = ".exe" if sys.platform == "win32" else ""
    executable_name = f"codex-quota-backend{executable_suffix}"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "codex-quota-backend",
        "--paths",
        str(PROJECT_ROOT),
        "--hidden-import",
        "app.main",
        "--collect-submodules",
        "app",
        "--add-data",
        f"{PROJECT_ROOT / 'app' / 'templates'}{os.pathsep}app/templates",
        "--add-data",
        f"{PROJECT_ROOT / 'app' / 'static'}{os.pathsep}app/static",
        "--distpath",
        str(BUILD_ROOT / "dist"),
        "--workpath",
        str(BUILD_ROOT / "work"),
        "--specpath",
        str(BUILD_ROOT / "spec"),
        str(PROJECT_ROOT / "app" / "desktop.py"),
    ]
    if sys.platform == "win32":
        command.append("--noconsole")
    subprocess.run(command, check=True)

    source = BUILD_ROOT / "dist" / executable_name
    destination = BINARY_DIR / f"codex-quota-backend-{args.target}{executable_suffix}"
    shutil.copy2(source, destination)
    if sys.platform != "win32":
        destination.chmod(destination.stat().st_mode | 0o111)

    print(f"Built desktop sidecar: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
