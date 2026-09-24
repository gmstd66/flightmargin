import importlib.util
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREPARE_SCRIPT = PROJECT_ROOT / "desktop" / "scripts" / "prepare-tauri-config.py"


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
