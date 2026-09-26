#!/usr/bin/env python3
"""Verify generated desktop manifests use the canonical Python version."""

import json
import sys
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TAURI_ROOT = PROJECT_ROOT / "desktop" / "src-tauri"

sys.path.insert(0, str(PROJECT_ROOT))

from app.version import __version__  # noqa: E402


def read_versions():
    cargo = tomllib.loads((TAURI_ROOT / "Cargo.toml").read_text(encoding="utf-8"))
    config = json.loads((TAURI_ROOT / "tauri.conf.json").read_text(encoding="utf-8"))
    return {
        "canonical Python version": __version__,
        "Cargo package version": cargo["package"]["version"],
        "Tauri application version": config["version"],
    }


def main():
    versions = read_versions()
    mismatches = {
        name: version
        for name, version in versions.items()
        if version != __version__
    }
    for name, version in versions.items():
        print(f"{name}: {version}")
    if mismatches:
        raise SystemExit("Desktop version synchronization failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
