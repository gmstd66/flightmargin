import json
from pathlib import Path

from app.about import APP_NAME
from app.systemd import render_systemd_unit
from app.core.config import AppConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_public_product_name_is_consistent():
    dashboard = (PROJECT_ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    settings = (PROJECT_ROOT / "app" / "templates" / "settings.html").read_text(encoding="utf-8")
    placeholder = (PROJECT_ROOT / "desktop" / "frontend" / "index.html").read_text(encoding="utf-8")

    assert APP_NAME == "FlightMargin"
    for content in (dashboard, settings, placeholder):
        assert "FlightMargin" in content
    assert "Codex Quota Monitor" not in dashboard
    assert "Codex Quota Monitor" not in settings
    assert "Codex Quota Monitor" not in placeholder


def test_tauri_and_installer_use_stable_flightmargin_identity():
    config = json.loads(
        (PROJECT_ROOT / "desktop" / "src-tauri" / "tauri.conf.template.json").read_text(
            encoding="utf-8"
        )
    )

    assert config["productName"] == "FlightMargin"
    assert config["identifier"] == "io.github.gmstd66.flightmargin"
    assert config["app"]["windows"][0]["title"] == "FlightMargin"
    assert config["bundle"]["publisher"] == "FlightMargin contributors"
    assert config["bundle"]["windows"]["nsis"]["startMenuFolder"] == "FlightMargin"


def test_windows_workflow_stages_flightmargin_artifacts_without_publishing():
    workflow = (
        PROJECT_ROOT / ".github" / "workflows" / "windows-beta-build.yml"
    ).read_text(encoding="utf-8")

    assert '"FlightMargin-$version-Windows-x64.exe"' in workflow
    assert "flightmargin-windows-unsigned-${{ github.sha }}" in workflow
    assert "workflow_dispatch:" in workflow
    assert "release:" not in workflow


def test_linux_service_description_uses_public_identity(tmp_path):
    config = AppConfig(
        app_root=tmp_path,
        data_dir=tmp_path / "data",
        database_path=tmp_path / "data" / "quota.db",
        host="127.0.0.1",
        port=18020,
        sample_seconds=60,
        codex_bin="/usr/bin/codex",
        desktop_mode=False,
    )

    unit = render_systemd_unit(
        config,
        user="flightmargin",
        cli_executable="/opt/flightmargin/venv/bin/flightmargin",
    )
    assert "Description=FlightMargin" in unit
    assert 'ExecStart="/opt/flightmargin/venv/bin/flightmargin" serve' in unit


def test_standard_agpl_license_is_present():
    license_text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")

    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in license_text
    assert "Version 3, 19 November 2007" in license_text
    assert "END OF TERMS AND CONDITIONS" in license_text
