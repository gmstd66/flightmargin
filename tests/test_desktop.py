import importlib.util
import socket
from pathlib import Path

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


def test_tauri_templates_use_canonical_version(tmp_path):
    module = load_prepare_module()

    for source, _destination in module.TEMPLATES:
        destination = tmp_path / source.name
        module.render_template(source, destination)
        assert "__APP_VERSION__" not in destination.read_text(encoding="utf-8")
        assert __version__ in destination.read_text(encoding="utf-8")
