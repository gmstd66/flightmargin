from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = PROJECT_ROOT / "scripts" / "install-linux.sh"
LINUX_GUIDE = PROJECT_ROOT / "docs" / "installation-linux.md"


def read_text(path):
    return path.read_text(encoding="utf-8")


def test_linux_installer_keeps_localhost_default():
    script = read_text(INSTALLER)

    assert 'HOST="127.0.0.1"' in script
    assert "LAN_MODE=0" in script


def test_linux_installer_lan_mode_uses_wildcard_binding():
    script = read_text(INSTALLER)

    assert "--lan)" in script
    assert 'HOST="0.0.0.0"' in script
    assert 'fail "--lan cannot be combined with --host"' in script


def test_linux_guide_recommends_resilient_lan_mode():
    guide = read_text(LINUX_GUIDE)

    assert "## 6. LAN installation" in guide
    assert "--lan" in guide
    assert "DHCP-assigned address" in guide
    assert "--host 192.168.1.50" not in guide
