#!/usr/bin/env python3
"""Verify the required metadata and package files in a release wheel."""

from __future__ import annotations

import sys
import zipfile
from email.parser import BytesParser
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from app.version import __version__


PROJECT_NAME = "flightmargin"
WHEEL_PREFIX = "flightmargin-"
REQUIRED_FILES = {
    "app/templates/index.html",
    "app/static/app.css",
    "app/static/app.js",
}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def find_wheel(directory: Path) -> Path:
    wheels = sorted(directory.glob("*.whl"))

    if len(wheels) != 1:
        fail(f"expected exactly one wheel in {directory}, found {len(wheels)}")

    wheel = wheels[0]
    package_version = __version__.replace("-beta.", "b")
    expected_name = f"{WHEEL_PREFIX}{package_version}-py3-none-any.whl"

    if wheel.name != expected_name:
        fail(f"expected {expected_name}, found {wheel.name}")

    return wheel


def verify_wheel(wheel: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

        missing = REQUIRED_FILES - names
        if missing:
            fail("wheel is missing " + ", ".join(sorted(missing)))

        metadata_paths = [
            name
            for name in names
            if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_paths) != 1:
            fail("wheel must contain exactly one METADATA file")

        metadata = BytesParser().parsebytes(
            archive.read(metadata_paths[0])
        )
        if metadata["Name"] != PROJECT_NAME:
            fail(f"metadata Name is {metadata['Name']!r}")
        if metadata["Version"] != __version__.replace("-beta.", "b"):
            fail(f"metadata Version is {metadata['Version']!r}")
        license_expression = metadata.get(
            "License-Expression",
            metadata.get("License"),
        )
        if license_expression != "AGPL-3.0-or-later":
            fail(f"metadata license is {license_expression!r}")

        license_paths = [
            name
            for name in names
            if name.endswith(".dist-info/licenses/LICENSE")
        ]
        if len(license_paths) != 1:
            fail("wheel must contain exactly one LICENSE file")
        license_text = archive.read(license_paths[0]).decode("utf-8")
        if "GNU AFFERO GENERAL PUBLIC LICENSE" not in license_text:
            fail("wheel LICENSE is not GNU AGPL v3")

        entry_point_paths = [
            name
            for name in names
            if name.endswith(".dist-info/entry_points.txt")
        ]
        if len(entry_point_paths) != 1:
            fail("wheel must contain exactly one entry_points.txt file")

        entry_points = archive.read(entry_point_paths[0]).decode("utf-8")
        if "flightmargin = app.cli:main" not in entry_points:
            fail("wheel console entry point flightmargin is missing")
        if "codex-quota = app.cli:main" not in entry_points:
            fail("wheel console entry point codex-quota is missing")


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    directory = Path(argv[0]) if argv else Path("dist")

    if len(argv) > 1:
        fail("usage: verify-release.py [DIST_DIRECTORY]")
    if not directory.is_dir():
        fail(f"artifact directory does not exist: {directory}")

    wheel = find_wheel(directory)
    verify_wheel(wheel)
    print(f"Verified release artifact: {wheel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
