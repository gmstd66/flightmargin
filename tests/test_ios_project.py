from __future__ import annotations

import plistlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IOS = ROOT / "ios"
PROJECT = IOS / "FlightMargin.xcodeproj" / "project.pbxproj"
INFO = IOS / "FlightMargin" / "Resources" / "Info.plist"
PRIVACY = IOS / "FlightMargin" / "Resources" / "PrivacyInfo.xcprivacy"
APP_ENTITLEMENTS = IOS / "FlightMargin" / "Resources" / "FlightMargin.entitlements"
WIDGET_ENTITLEMENTS = IOS / "FlightMarginWidget" / "FlightMarginWidget.entitlements"
APP_GROUP = "group.io.github.gmstd66.flightmargin"
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
    ) + list((IOS / "FlightMarginWidget").glob("*.swift")) + list(
        (IOS / "Shared").glob("*.swift")
    )
    assert swift_files
    for path in swift_files:
        expected_builds = 2 if path.name == "WidgetSnapshot.swift" else 1
        assert project.count(f"{path.name} in Sources") == expected_builds, path
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


def _build_settings(project: str, configuration_id: str) -> dict[str, str]:
    match = re.search(
        rf"{re.escape(configuration_id)} .*?buildSettings = \{{(.*?)\}}; name =",
        project,
    )
    assert match is not None, configuration_id
    settings = {}
    for key, quoted, plain in re.findall(
        r'(\w+) = (?:"([^"]*)"|([^;]*));', match.group(1)
    ):
        settings[key] = quoted or plain.strip()
    return settings


def test_ios_build_identity_and_deployment_target_are_fixed():
    project = PROJECT.read_text(encoding="utf-8")
    app_debug = _build_settings(project, "E50000000000000000000001")
    app_release = _build_settings(project, "E50000000000000000000002")
    tests_debug = _build_settings(project, "E50000000000000000000003")
    tests_release = _build_settings(project, "E50000000000000000000004")
    configurations = (app_debug, app_release, tests_debug, tests_release)

    assert all(settings["IPHONEOS_DEPLOYMENT_TARGET"] == "17.0" for settings in configurations)
    assert app_debug["PRODUCT_BUNDLE_IDENTIFIER"] == "com.gmstd.flightmargin.dev"
    assert app_release["PRODUCT_BUNDLE_IDENTIFIER"] == "io.github.gmstd66.flightmargin"
    assert tests_debug["PRODUCT_BUNDLE_IDENTIFIER"] == "com.gmstd.flightmargin.dev.tests"
    assert tests_release["PRODUCT_BUNDLE_IDENTIFIER"] == "io.github.gmstd66.flightmargin.tests"
    assert app_debug["MARKETING_VERSION"] == app_release["MARKETING_VERSION"] == "0.1.0"
    assert app_debug["CURRENT_PROJECT_VERSION"] == app_release["CURRENT_PROJECT_VERSION"] == "2"
    assert app_debug["CODE_SIGN_STYLE"] == "Automatic"
    assert "PROVISIONING_PROFILE_SPECIFIER" not in app_debug
    assert app_release["CODE_SIGN_STYLE"] == "Manual"
    assert app_release["CODE_SIGN_IDENTITY"] == "iPhone Distribution"
    assert app_release["DEVELOPMENT_TEAM"] == "JL2WCD3FDQ"
    assert app_release["PROVISIONING_PROFILE_SPECIFIER"] == "FlightMargin App Store"
    assert tests_debug["CODE_SIGN_STYLE"] == tests_release["CODE_SIGN_STYLE"] == "Automatic"
    assert "SUPPORTED_PLATFORMS = \"iphoneos iphonesimulator\"" in project


def test_widget_target_app_group_embedding_and_signing_are_configured():
    project = PROJECT.read_text(encoding="utf-8")
    widget_debug = _build_settings(project, "E50000000000000000000007")
    widget_release = _build_settings(project, "E50000000000000000000008")

    assert re.search(
        r"[A-F0-9]{24} /\* FlightMarginWidget \*/ = \{isa = PBXNativeTarget",
        project,
    )
    assert widget_debug["PRODUCT_BUNDLE_IDENTIFIER"] == "com.gmstd.flightmargin.dev.widget"
    assert widget_release["PRODUCT_BUNDLE_IDENTIFIER"] == "io.github.gmstd66.flightmargin.widget"
    assert widget_debug["CODE_SIGN_STYLE"] == "Automatic"
    assert "PROVISIONING_PROFILE_SPECIFIER" not in widget_debug
    assert widget_release["CODE_SIGN_STYLE"] == "Manual"
    assert widget_release["DEVELOPMENT_TEAM"] == "JL2WCD3FDQ"
    assert widget_release["PROVISIONING_PROFILE_SPECIFIER"] == "FlightMargin Widget App Store"
    assert widget_debug["CURRENT_PROJECT_VERSION"] == widget_release["CURRENT_PROJECT_VERSION"] == "2"
    assert "FlightMarginWidget.appex in Embed App Extensions" in project
    assert "dstSubfolderSpec = 13" in project

    for entitlements in (APP_ENTITLEMENTS, WIDGET_ENTITLEMENTS):
        with entitlements.open("rb") as handle:
            values = plistlib.load(handle)
        assert values["com.apple.security.application-groups"] == [APP_GROUP]


def test_widget_is_medium_only_and_has_no_network_or_keychain_access():
    widget_source = (IOS / "FlightMarginWidget" / "FlightMarginWidget.swift").read_text(
        encoding="utf-8"
    )
    project = PROJECT.read_text(encoding="utf-8")
    widget_phase = re.search(
        r"F30000000000000000000003 = \{isa = PBXSourcesBuildPhase;.*?files = \((.*?)\);",
        project,
    )
    assert widget_phase is not None
    assert ".supportedFamilies([.systemMedium])" in widget_source
    assert "URLSession" not in widget_source
    assert "RelayAPIClient.swift" not in widget_phase.group(1)
    assert "KeychainStore.swift" not in widget_phase.group(1)
    assert "DeviceIdentity.swift" not in widget_phase.group(1)


def test_shared_widget_snapshot_declares_only_sanitized_display_fields():
    source = (IOS / "Shared" / "WidgetSnapshot.swift").read_text(encoding="utf-8")
    forbidden = (
        "credential", "pairingToken", "manualCode", "deviceID", "deviceUUID",
        "bearerToken", "requestBody", "responseBody", "prompt", "transcript",
    )
    for name in forbidden:
        assert name not in source
    assert "historyLimit = 72" in source
    assert "options: .atomic" in source


def test_flightmargin_url_scheme_is_registered():
    with INFO.open("rb") as handle:
        info = plistlib.load(handle)
    schemes = {
        scheme
        for entry in info["CFBundleURLTypes"]
        for scheme in entry["CFBundleURLSchemes"]
    }
    assert schemes == {"flightmargin"}
    assert info["CFBundleURLTypes"][0]["CFBundleURLName"] == (
        "io.github.gmstd66.flightmargin.pairing"
    )
    assert info["ITSAppUsesNonExemptEncryption"] is False
    ats = info["NSAppTransportSecurity"]
    assert ats == {"NSAllowsLocalNetworking": True}


def test_privacy_manifest_declares_only_app_private_user_defaults_reason():
    assert PRIVACY.is_file()
    with PRIVACY.open("rb") as handle:
        privacy = plistlib.load(handle)
    assert privacy["NSPrivacyTracking"] is False
    assert privacy["NSPrivacyAccessedAPITypes"] == [
        {
            "NSPrivacyAccessedAPIType": "NSPrivacyAccessedAPICategoryUserDefaults",
            "NSPrivacyAccessedAPITypeReasons": ["CA92.1"],
        }
    ]
    assert "NSPrivacyCollectedDataTypes" not in privacy


def test_privacy_manifest_is_in_application_resources():
    project = PROJECT.read_text(encoding="utf-8")
    build_file = re.search(
        r"([A-F0-9]{24}) /\* PrivacyInfo\.xcprivacy in Resources \*/ = "
        r"\{isa = PBXBuildFile; fileRef = ([A-F0-9]{24}) ",
        project,
    )
    assert build_file is not None
    app_resources = re.search(
        r"F20000000000000000000001 = \{isa = PBXResourcesBuildPhase;.*?files = \((.*?)\);",
        project,
    )
    assert app_resources is not None
    assert build_file.group(1) in app_resources.group(1)
    assert f"{build_file.group(2)} /* PrivacyInfo.xcprivacy */" in project


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


def test_pairing_claim_device_uuid_is_encoded_as_lowercase_text():
    models = (IOS / "FlightMargin" / "Models" / "RelayModels.swift").read_text(
        encoding="utf-8"
    )
    support = (IOS / "FlightMarginTests" / "TestSupport.swift").read_text(
        encoding="utf-8"
    )
    client_tests = (
        IOS / "FlightMarginTests" / "RelayAPIClientTests.swift"
    ).read_text(encoding="utf-8")
    expected = "aabbccdd-eeff-4a4b-8c8d-aabbccddeeff"
    assert "deviceID.uuidString.lowercased()" in models
    assert "AABBCCDD-EEFF-4A4B-8C8D-AABBCCDDEEFF" in support
    assert client_tests.count(expected) >= 4
    assert client_tests.count("XCTAssertEqual(result.deviceID, testIdentity.deviceID)") == 2


def test_failed_manual_pairing_clears_input_before_presenting_local_error():
    pairing_view = (
        IOS / "FlightMargin" / "Views" / "PairingView.swift"
    ).read_text(encoding="utf-8")
    callback = re.search(
        r"state\.pair\(manualInput:\s*code\)\s*\{\s*message\s+in"
        r"(?P<body>.*?)\n\s*\}",
        pairing_view,
        re.DOTALL,
    )
    assert callback is not None
    body = callback.group("body")
    clear_position = body.find('code = ""')
    error_position = body.find("pairingError = message")
    assert 0 <= clear_position < error_position
    assert "get: { pairingError != nil }" in pairing_view
    assert 'Text(pairingError ?? "")' in pairing_view


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
