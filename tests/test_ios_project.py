from __future__ import annotations

import plistlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IOS = ROOT / "ios"
PROJECT = IOS / "FlightMargin.xcodeproj" / "project.pbxproj"
INFO = IOS / "FlightMargin" / "Resources" / "Info.plist"
PRODUCTION_ENDPOINT = (
    "https://samcdyrwfwrlxzypzgmj.supabase.co/functions/v1/relay-v1"
)


def test_ios_project_and_expected_layout_exist():
    assert PROJECT.is_file()
    expected_directories = {
        "App", "Models", "Networking", "Security", "Pairing", "Views"
    }
    source_root = IOS / "FlightMargin"
    assert expected_directories <= {path.name for path in source_root.iterdir() if path.is_dir()}
    assert (IOS / "FlightMarginTests").is_dir()


def test_every_swift_source_is_referenced_and_built():
    project = PROJECT.read_text(encoding="utf-8")
    swift_files = list((IOS / "FlightMargin").rglob("*.swift")) + list(
        (IOS / "FlightMarginTests").glob("*.swift")
    )
    assert swift_files
    for path in swift_files:
        assert project.count(f"{path.name} in Sources") == 1, path
        assert project.count(f"/* {path.name} */") >= 2, path


def test_pbxproj_and_shared_scheme_references_are_consistent():
    project = PROJECT.read_text(encoding="utf-8")
    identifiers = set(re.findall(r"(?m)^\s*([A-F0-9]{24})\b.*=", project))
    references = set(re.findall(r"\b[A-F0-9]{24}\b", project))
    assert references == identifiers
    scheme = (
        IOS / "FlightMargin.xcodeproj" / "xcshareddata" / "xcschemes"
        / "FlightMargin.xcscheme"
    ).read_text(encoding="utf-8")
    blueprint_ids = set(re.findall(r'BlueprintIdentifier="([A-F0-9]{24})"', scheme))
    assert blueprint_ids <= identifiers


def test_ios_build_identity_and_deployment_target_are_fixed():
    project = PROJECT.read_text(encoding="utf-8")
    assert project.count("IPHONEOS_DEPLOYMENT_TARGET = 17.0") == 4
    assert project.count("PRODUCT_BUNDLE_IDENTIFIER = com.gmstd.flightmargin.dev;") == 2
    assert "SUPPORTED_PLATFORMS = \"iphoneos iphonesimulator\"" in project


def test_flightmargin_url_scheme_is_registered():
    with INFO.open("rb") as handle:
        info = plistlib.load(handle)
    schemes = {
        scheme
        for entry in info["CFBundleURLTypes"]
        for scheme in entry["CFBundleURLSchemes"]
    }
    assert schemes == {"flightmargin"}
    ats = info["NSAppTransportSecurity"]
    assert ats == {"NSAllowsLocalNetworking": True}


def test_no_swift_packages_or_third_party_runtime_sdks():
    project = PROJECT.read_text(encoding="utf-8")
    all_swift = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (IOS / "FlightMargin").rglob("*.swift")
    )
    assert "XCRemoteSwiftPackageReference" not in project
    assert "XCSwiftPackageProductDependency" not in project
    assert not list(IOS.rglob("Package.resolved"))
    for forbidden in (
        "import Supabase", "import Firebase", "import Sentry", "import AppCenter",
        "import Mixpanel", "import Segment", "import Amplitude",
    ):
        assert forbidden not in all_swift


def test_production_endpoint_and_keychain_privacy_guards():
    sources = {
        path.name: path.read_text(encoding="utf-8")
        for path in (IOS / "FlightMargin").rglob("*.swift")
    }
    assert PRODUCTION_ENDPOINT in sources["RelayAPIClient.swift"]
    assert "kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly" in sources["KeychainStore.swift"]
    assert "kSecAttrSynchronizable" in sources["KeychainStore.swift"]
    assert "UserDefaults" not in sources["KeychainStore.swift"]
    assert "credential" not in re.findall(
        r'static let \w+ = "([^"]+)"', sources["AppState.swift"]
    )
    all_source = "\n".join(sources.values())
    assert "print(" not in all_source
    assert "Logger(" not in all_source
    assert "UIDevice.current.name" not in all_source


def test_no_obvious_committed_ios_secrets():
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in IOS.rglob("*")
        if path.is_file() and path.suffix in {".swift", ".plist", ".pbxproj", ".xcscheme"}
    )
    patterns = (
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        r"(?i)(?:service_role|supabase_service_role|openai_api_key)\s*[=:]\s*['\"][A-Za-z0-9_-]{16,}",
        r"sk-[A-Za-z0-9_-]{32,}",
    )
    for pattern in patterns:
        assert re.search(pattern, text) is None


def test_url_protocol_claim_tests_accept_streamed_request_bodies():
    support = (IOS / "FlightMarginTests" / "TestSupport.swift").read_text(
        encoding="utf-8"
    )
    client_tests = (
        IOS / "FlightMarginTests" / "RelayAPIClientTests.swift"
    ).read_text(encoding="utf-8")
    assert "request.httpBodyStream" in support
    assert "requestBodyData(request)" in client_tests
    assert "request.httpBody!" not in client_tests


def test_relay_request_tests_assert_complete_production_paths():
    support = (IOS / "FlightMarginTests" / "TestSupport.swift").read_text(
        encoding="utf-8"
    )
    client_tests = (
        IOS / "FlightMarginTests" / "RelayAPIClientTests.swift"
    ).read_text(encoding="utf-8")
    assert (
        "RelayAPIClient.productionEndpoint.appendingPathComponent(route).path"
        in support
    )
    assert client_tests.count(
        'assertProductionRelayPath(request, appending: "v1/pairings/claim")'
    ) == 2
    assert 'assertProductionRelayPath(request, appending: "v1/quota")' in client_tests
    assert '"/relay-v1/v1/pairings/claim"' not in client_tests
