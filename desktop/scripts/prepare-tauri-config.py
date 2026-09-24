#!/usr/bin/env python3
"""Generate Tauri manifests from the canonical Python package version."""

import sys
from pathlib import Path


DESKTOP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = DESKTOP_ROOT.parent
TAURI_ROOT = DESKTOP_ROOT / "src-tauri"
TEMPLATES = (
    (TAURI_ROOT / "Cargo.template.toml", TAURI_ROOT / "Cargo.toml"),
    (TAURI_ROOT / "tauri.conf.template.json", TAURI_ROOT / "tauri.conf.json"),
)

sys.path.insert(0, str(PROJECT_ROOT))

from app.version import __version__  # noqa: E402


def render_template(source, destination, version=__version__):
    content = source.read_text(encoding="utf-8")
    marker = "__APP_VERSION__"

    if content.count(marker) != 1:
        raise ValueError(f"Expected one version marker in {source}")

    destination.write_text(
        content.replace(marker, version),
        encoding="utf-8",
    )


def main():
    for source, destination in TEMPLATES:
        render_template(source, destination)
        print(f"Generated {destination.relative_to(DESKTOP_ROOT.parent)}")


if __name__ == "__main__":
    main()
