from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SETTINGS = (PROJECT_ROOT / "app/templates/settings.html").read_text(encoding="utf-8")
SCRIPT = (PROJECT_ROOT / "app/static/settings.js").read_text(encoding="utf-8")
QR_SCRIPT = PROJECT_ROOT / "app/static/qrcode.min.js"


def test_mobile_relay_settings_are_integrated_and_opt_in():
    assert 'data-settings-tab="relay"' in SETTINGS
    assert 'id="relayEnabled"' in SETTINGS
    assert "Enable Mobile Relay" in SETTINGS
    assert "Pair mobile device" in SETTINGS
    assert "iPhone app" not in SETTINGS


def test_pairing_is_user_initiated_and_expiration_clears_browser_state():
    assert 'addEventListener("click"' in SCRIPT
    assert 'fetch("/api/relay/pairings", { method: "POST" })' in SCRIPT
    assert "loadRelay" in SCRIPT
    assert "Request a new code" in SCRIPT
    assert "pairingInformation = null" in SCRIPT
    assert "pairingDeadline = null" in SCRIPT
    assert "Date.now() + 5 * 60 * 1000" in SCRIPT
    assert 'pairingQr.replaceChildren()' in SCRIPT
    assert 'pairingQr.removeAttribute("title")' in SCRIPT


def test_qr_uses_returned_deep_link_and_has_no_runtime_cdn():
    assert "text: information.deep_link" in SCRIPT
    assert '<script src="/static/qrcode.min.js?v=1"></script>' in SETTINGS
    assert QR_SCRIPT.is_file()
    assert "https://" not in QR_SCRIPT.read_text(encoding="utf-8")
