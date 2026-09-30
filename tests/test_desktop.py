import importlib.util
import json
import socket
import sys
import types
from pathlib import Path

import app.desktop as desktop_module

from app.desktop import (
    LOOPBACK_HOST,
    READINESS_PREFIX,
    configure_desktop_environment,
    create_loopback_socket,
    parse_args,
)
from app.version import __version__
from app.core.config import default_desktop_log_dir


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREPARE_SCRIPT = PROJECT_ROOT / "desktop" / "scripts" / "prepare-tauri-config.py"
TAURI_MAIN = PROJECT_ROOT / "desktop" / "src-tauri" / "src" / "main.rs"
TAURI_CONFIG = PROJECT_ROOT / "desktop" / "src-tauri" / "tauri.conf.template.json"
TAURI_CARGO = PROJECT_ROOT / "desktop" / "src-tauri" / "Cargo.template.toml"
TAURI_CAPABILITY = PROJECT_ROOT / "desktop" / "src-tauri" / "capabilities" / "default.json"
OPEN_SETTINGS_CAPABILITY = PROJECT_ROOT / "desktop" / "src-tauri" / "capabilities" / "open-settings.json"
CLOSE_SETTINGS_CAPABILITY = PROJECT_ROOT / "desktop" / "src-tauri" / "capabilities" / "close-settings.json"
OPEN_PROJECT_LINK_CAPABILITY = PROJECT_ROOT / "desktop" / "src-tauri" / "capabilities" / "open-project-link.json"
TAURI_BUILD = PROJECT_ROOT / "desktop" / "src-tauri" / "build.rs"
DESKTOP_JS = PROJECT_ROOT / "app" / "static" / "app.js"
SETTINGS_JS = PROJECT_ROOT / "app" / "static" / "settings.js"
SETTINGS_TEMPLATE = PROJECT_ROOT / "app" / "templates" / "settings.html"
DESKTOP_CSS = PROJECT_ROOT / "app" / "static" / "app.css"
DESKTOP_PACKAGE = PROJECT_ROOT / "desktop" / "package.json"
INSTALLER_HOOKS = PROJECT_ROOT / "desktop" / "src-tauri" / "windows" / "installer-hooks.nsh"
WINDOWS_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "windows-beta-build.yml"
VERSION_CHECK = PROJECT_ROOT / "scripts" / "verify-desktop-version.py"


def load_prepare_module():
    spec = importlib.util.spec_from_file_location(
        "prepare_tauri_config",
        PREPARE_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_desktop_parser_defaults_to_ephemeral_port():
    args = parse_args([])

    assert args.port == 0
    assert args.data_dir is None


def test_desktop_environment_forces_loopback_and_desktop_mode(monkeypatch, tmp_path):
    monkeypatch.delenv("CODEX_QUOTA_DESKTOP", raising=False)
    monkeypatch.delenv("CODEX_QUOTA_HOST", raising=False)
    monkeypatch.delenv("CODEX_QUOTA_DATA_DIR", raising=False)

    args = parse_args(["--data-dir", str(tmp_path)])
    configure_desktop_environment(args)

    assert __import__("os").environ["CODEX_QUOTA_DESKTOP"] == "1"
    assert __import__("os").environ["CODEX_QUOTA_HOST"] == LOOPBACK_HOST
    assert __import__("os").environ["CODEX_QUOTA_DATA_DIR"] == str(tmp_path)


def test_desktop_socket_is_loopback_and_os_selects_port():
    listener = create_loopback_socket()

    try:
        host, port = listener.getsockname()
        assert host == LOOPBACK_HOST
        assert port != 0

        with socket.create_connection((host, port), timeout=1):
            pass
    finally:
        listener.close()


def test_readiness_line_format():
    assert f"{READINESS_PREFIX}18001" == "CODEX_QUOTA_DESKTOP_PORT=18001"


def test_desktop_server_uses_bound_socket(monkeypatch, tmp_path):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind((LOOPBACK_HOST, 0))
    listener.listen()
    captured = {}

    class FakeConfig:
        def __init__(self, app, **kwargs):
            captured["app"] = app
            captured["config_kwargs"] = kwargs

    class FakeServer:
        def __init__(self, config):
            captured["config"] = config

        def run(self, sockets):
            captured["sockets"] = sockets

    try:
        monkeypatch.setitem(
            sys.modules,
            "app.main",
            types.SimpleNamespace(app=object()),
        )
        monkeypatch.setattr(desktop_module, "create_loopback_socket", lambda port: listener)
        monkeypatch.setattr(desktop_module.uvicorn, "Config", FakeConfig)
        monkeypatch.setattr(desktop_module.uvicorn, "Server", FakeServer)

        assert desktop_module.main(["--data-dir", str(tmp_path)]) == 0
        assert captured["sockets"] == [listener]
        assert "fd" not in captured["config_kwargs"]
    finally:
        listener.close()


def test_tauri_templates_use_canonical_version(tmp_path):
    module = load_prepare_module()

    for source, _destination in module.TEMPLATES:
        destination = tmp_path / source.name
        module.render_template(source, destination)
        assert "__APP_VERSION__" not in destination.read_text(encoding="utf-8")
        assert __version__ in destination.read_text(encoding="utf-8")


def test_tauri_release_profile_uses_safe_size_optimizations():
    manifest = TAURI_CARGO.read_text(encoding="utf-8")

    assert '[profile.release]' in manifest
    assert 'codegen-units = 1' in manifest
    assert 'lto = "thin"' in manifest
    assert 'strip = "symbols"' in manifest
    assert 'panic = "abort"' not in manifest


def test_windows_desktop_logs_share_the_application_data_root():
    local_app_data = Path("C:/Users/test/AppData/Local")

    assert default_desktop_log_dir(
        system="Windows",
        environ={"LOCALAPPDATA": str(local_app_data)},
        home="C:/Users/test",
    ) == local_app_data / "FlightMargin" / "logs"


def test_release_tauri_binary_uses_windows_gui_subsystem():
    source = TAURI_MAIN.read_text(encoding="utf-8")
    assert '#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]' in source


def test_dashboard_uses_fixed_reflowing_panels_and_visibility_only_controls():
    source = DESKTOP_JS.read_text(encoding="utf-8")
    settings_source = SETTINGS_JS.read_text(encoding="utf-8")
    styles = DESKTOP_CSS.read_text(encoding="utf-8")
    template = (PROJECT_ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")

    assert "dragHandle" not in source
    assert "resizeHandle" not in source
    assert "data-size" not in source
    assert 'document.getElementById("panelSettings").addEventListener("change"' in settings_source
    assert 'document.getElementById("showAllPanels")' in settings_source
    assert "historyBecameVisible" in source
    assert "requestAnimationFrame(() => { void loadHistory(); })" in source
    assert "grid-auto-flow:dense" in styles
    assert "draggable=" not in template
    assert 'id="showAllPanels"' not in template


def test_history_panel_fills_remaining_dashboard_height():
    styles = DESKTOP_CSS.read_text(encoding="utf-8")
    template = (PROJECT_ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    grid_end = template.index("</section>", template.index('id="dashboardGrid"'))
    history_start = template.index('data-panel="history"')

    assert grid_end < history_start
    assert "height:100vh" in styles
    assert ".container > main { flex:1 1 auto; min-height:0; display:grid; grid-template-rows:auto minmax(0, 1fr);" in styles
    assert ".history-card { grid-column:1; }" in styles
    assert ".history-card { min-height:0; height:100%;" in styles
    assert ".history-card canvas { flex:1 1 auto; min-height:0; height:100%; }" in styles
    assert "height:clamp(92px,18vh,160px)" not in styles
    assert "min-height:92px" not in styles
    assert "min-height:38px" not in styles


def test_tauri_release_build_rebuilds_embedded_dashboard_sidecar():
    package = json.loads(DESKTOP_PACKAGE.read_text(encoding="utf-8"))
    scripts = package["scripts"]

    assert scripts["prepare"] == "..\\.venv\\Scripts\\python.exe scripts/prepare-tauri-config.py"
    assert scripts["build:sidecar"] == "..\\.venv\\Scripts\\python.exe scripts/build-sidecar.py"
    assert scripts["tauri:build"].startswith("npm run build:sidecar &&")


def test_sidecar_build_excludes_optional_build_environment_packages():
    source = (
        PROJECT_ROOT / "desktop" / "scripts" / "build-sidecar.py"
    ).read_text(encoding="utf-8")

    assert '"--collect-submodules",\n        "app",' in source
    assert '"--exclude-module",\n        "setuptools",' in source
    assert '"--exclude-module",\n        "yaml",' in source


def test_windows_beta_workflow_is_manual_locked_and_nonpublishing():
    workflow = WINDOWS_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "npm ci" in workflow
    assert workflow.index("npm run build:sidecar") < workflow.index("cargo check --locked")
    assert "cargo check --locked" in workflow
    assert "cargo test --locked" in workflow
    assert "npm run tauri:build" in workflow
    assert "Get-FileHash" in workflow
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7" in workflow
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7" in workflow
    assert "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7" in workflow
    assert "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4" in workflow
    assert "release-artifacts/" in workflow
    assert "release:" not in workflow
    assert "SIGNPATH" not in workflow


def test_desktop_version_check_uses_canonical_version():
    source = VERSION_CHECK.read_text(encoding="utf-8")

    assert "from app.version import __version__" in source
    assert 'TAURI_ROOT / "Cargo.toml"' in source
    assert 'TAURI_ROOT / "tauri.conf.json"' in source
    assert "version != __version__" in source


def test_nsis_upgrade_hook_prompts_for_clean_tray_quit_without_killing():
    config = json.loads(TAURI_CONFIG.read_text(encoding="utf-8"))
    hooks = INSTALLER_HOOKS.read_text(encoding="utf-8")

    assert config["bundle"]["windows"]["nsis"]["installerHooks"] == "./windows/installer-hooks.nsh"
    assert "NSIS_HOOK_PREINSTALL" in hooks
    assert 'FindProcessCurrentUser "codex-quota-backend.exe"' in hooks
    assert "Fully Quit it from the system tray" in hooks
    assert "MB_RETRYCANCEL" in hooks
    assert "KillProcess" not in hooks
    assert "taskkill" not in hooks.lower()


def test_dashboard_assets_are_revisioned_for_desktop_webview_cache():
    template = (PROJECT_ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    assert '/static/app.css?v=15' in template
    assert '/static/app.js?v=14' in template


def test_compact_history_uses_smaller_y_axis_labels_without_changing_ticks():
    source = DESKTOP_JS.read_text(encoding="utf-8")

    assert "const left = compact ? 28 : 46;" in source
    assert "const yAxisFontSize = compact ? 8 : 11;" in source
    assert "ctx.font = `${yAxisFontSize}px system-ui`;" in source
    assert "[0, 25, 50, 75, 100]" in source
    assert '"9px system-ui"' in source


def test_settings_uses_one_native_window_with_loopback_ipc_and_tray_guidance():
    source = DESKTOP_JS.read_text(encoding="utf-8")
    settings_source = SETTINGS_JS.read_text(encoding="utf-8")
    rust = TAURI_MAIN.read_text(encoding="utf-8")
    dashboard = (PROJECT_ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    settings = (PROJECT_ROOT / "app" / "templates" / "settings.html").read_text(encoding="utf-8")
    config = TAURI_CONFIG.read_text(encoding="utf-8")
    capability = TAURI_CAPABILITY.read_text(encoding="utf-8")

    assert 'invoke("open_settings")' in source
    assert "__TAURI_INTERNALS__?.invoke" in source
    assert 'get_webview_window(SETTINGS_WINDOW_LABEL)' in rust
    assert "adjacent_window_position" in rust
    assert 'label == "main"' in rust
    assert '"withGlobalTauri": true' in config
    assert '"http://127.0.0.1:*/*"' in capability
    assert '"main", "settings"' in capability
    assert "settingsDialog" not in dashboard
    assert "showModal" not in source
    assert 'tauriInvoke("close_settings")' in settings_source
    assert "Windows may place quota indicators in the hidden-icons menu." in settings
    assert "Drag them from ^ to the system tray to keep them visible." in settings


def test_native_settings_about_content_uses_dynamic_safe_metadata():
    settings = SETTINGS_TEMPLATE.read_text(encoding="utf-8")
    settings_source = SETTINGS_JS.read_text(encoding="utf-8")
    backend = (PROJECT_ROOT / "app" / "main.py").read_text(encoding="utf-8")

    assert 'data-settings-tab="about"' in settings
    assert "Monitor Codex capacity, pace, resets, and credits at a glance." in settings
    assert "History, preferences, and logs are stored locally on this computer." in settings
    assert "does not manage or store your OpenAI credentials" in settings
    assert "It includes no telemetry." in settings
    assert "AGPLv3-or-later" in settings
    assert "Unofficial community tool. Not affiliated with or endorsed by OpenAI." in settings
    assert "Technical details" in settings
    assert 'id="copyDiagnostics"' in settings
    assert 'fetch("/api/about"' in settings_source
    assert 'f"App version:' not in settings_source
    assert __version__ not in settings
    assert '@app.get("/api/about")' in backend
    assert "Source Code" in settings
    assert "Report an Issue" in settings
    assert "Sponsor" not in settings
    assert "https://github.com/gmstd66/flightmargin" in settings
    assert 'target="_blank" rel="noopener noreferrer"' in settings


def test_settings_commands_have_narrow_tauri_acl_capabilities():
    build_script = TAURI_BUILD.read_text(encoding="utf-8")
    open_capability = json.loads(OPEN_SETTINGS_CAPABILITY.read_text(encoding="utf-8"))
    close_capability = json.loads(CLOSE_SETTINGS_CAPABILITY.read_text(encoding="utf-8"))
    project_capability = json.loads(OPEN_PROJECT_LINK_CAPABILITY.read_text(encoding="utf-8"))

    for command in ("open_settings", "close_settings", "open_project_link"):
        assert f'"{command}"' in build_script
    assert open_capability["windows"] == ["main"]
    assert open_capability["permissions"] == ["allow-open-settings"]
    assert close_capability["windows"] == ["settings"]
    assert close_capability["permissions"] == ["allow-close-settings"]
    assert open_capability["remote"]["urls"] == ["http://127.0.0.1:*/*"]
    assert close_capability["remote"]["urls"] == ["http://127.0.0.1:*/*"]
    assert project_capability["windows"] == ["settings"]
    assert project_capability["permissions"] == ["allow-open-project-link"]
    assert project_capability["remote"]["urls"] == ["http://127.0.0.1:*/*"]


def test_tray_settings_and_about_reuse_the_native_settings_window():
    rust = TAURI_MAIN.read_text(encoding="utf-8")
    settings_source = SETTINGS_JS.read_text(encoding="utf-8")
    dashboard = (PROJECT_ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")

    assert 'MenuItem::with_id(app, "settings", "Settings..."' in rust
    assert 'MenuItem::with_id(app, "about", "About..."' in rust
    assert 'open_settings_window(app, SettingsSection::Dashboard)' in rust
    assert 'open_settings_window(app, SettingsSection::About)' in rust
    assert 'get_webview_window(SETTINGS_WINDOW_LABEL)' in rust
    assert rust.count("WebviewWindowBuilder::new(") == 1
    assert 'window.openSettingsSection?.' in rust
    assert 'url.set_query(Some(&format!("section={}"' in rust
    assert "window.openSettingsSection = openSettingsSection" in settings_source
    assert 'new URLSearchParams(window.location.search).get("section")' in settings_source
    assert '/static/settings.js?v=6' in SETTINGS_TEMPLATE.read_text(encoding="utf-8")
    assert "settingsDialog" not in dashboard
    assert "showModal" not in DESKTOP_JS.read_text(encoding="utf-8")


def test_credits_share_the_existing_tray_sample_and_preference_lifecycle():
    backend = (PROJECT_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    rust = TAURI_MAIN.read_text(encoding="utf-8")

    assert 'f"credits={credits if credits is not None else \'--\'}"' in backend
    assert 'const CREDITS_INDICATOR_ID: &str = "credits-indicator";' in rust
    assert "CREDITS_MARKER: [u8; 4] = [52, 211, 153, 255]" in rust
    assert "sync_credits_indicator(app, credits)" in rust
    assert "remove_tray_by_id(CREDITS_INDICATOR_ID)" in rust


def test_tray_startup_is_backward_compatible_and_failure_isolated():
    rust = TAURI_MAIN.read_text(encoding="utf-8")

    assert 'initialize_tray_icons(app.handle());' in rust
    assert 'match setup_tray(app)' in rust
    assert 'sync_quota_indicators(app, "--", "--", "--");' in rust
    assert 'if parts.len() >= 2' in rust
    assert '.get(2)' in rust
    assert rust.count("if let Err(error) = sync_") == 3
    assert "Tray indicator preference loaded: enabled={enabled}" in rust
    assert "Normal application tray icon created" in rust
