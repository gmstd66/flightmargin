# FlightMargin Internal TestFlight preparation

## Build identity

- Product: FlightMargin
- Platform: iOS
- Minimum OS: iOS 17.0
- Debug bundle: `com.gmstd.flightmargin.dev`
- Release bundle: `io.github.gmstd66.flightmargin`
- Marketing version: `0.1.0`
- Initial build: `1`
- Distribution target: Internal TestFlight only for the first physical-phone demo

The user has an active paid Apple Developer Program membership. Automatic
signing remains enabled, but `DEVELOPMENT_TEAM` is intentionally unset until
the Mac/Xcode step. Apple credentials, certificates, provisioning profiles,
and account details do not belong in Git.

No public App Store release is authorized. No external TestFlight testing is
authorized yet. This COXON task does not contact Apple or App Store Connect and
does not upload a TestFlight or App Store build.

## Explicitly pending before the next Xcode session

The following Apple-side/demo-preparation steps are intentionally pending and
have not yet been completed:

1. Register the explicit App ID `io.github.gmstd66.flightmargin` in Apple
   Developer Certificates, Identifiers & Profiles.
2. Create the FlightMargin iOS app record in App Store Connect using that
   bundle identifier.
3. Create the internal TestFlight group `FlightMargin Internal` and add the
   owner's App Store Connect account as an internal tester.
4. Generate and configure the repository-owned 1024x1024 iOS AppIcon from the
   existing FlightMargin artwork.

After those items, continue with the native Mac sequence below. No public App
Store submission or external TestFlight testing is part of this pending work.

## Privacy and export compliance

`PrivacyInfo.xcprivacy` declares the app-private `UserDefaults` access used for
non-secret pairing state, cached quota, and refresh state with required reason
`CA92.1`. A direct-source audit found no current use of another Apple
required-reason API category. The manifest declares no tracking and invents no
collected-data declarations.

The relay-bound UUID audit found only pairing claim `device_id` needed a casing
correction. The generated UUID component of the device credential was already
lowercased, and no other client-generated UUID field crosses the v1 request
boundary.

`ITSAppUsesNonExemptEncryption` is `NO`. The current app uses Apple platform
`URLSession`/HTTPS and ships no proprietary or third-party cryptography. Revisit
this declaration whenever cryptographic behavior or dependencies change.

## App icon

The repository's source artwork remains
`desktop/src-tauri/icons/app-icon.svg`. COXON has no already-installed suitable
SVG rasterizer, and no package or runtime dependency was added.

APP ICON PNG: DEFERRED TO MAC

Before archiving, create the repository-owned square 1024x1024 iOS icon from
that source, without transparent rounded outer corners; add it to an
`AppIcon.appiconset`, and configure the application target to use `AppIcon`.

## Native Mac sequence

1. Pull `dev/ios-testflight-demo` on Mac.
2. Run all native XCTest.
3. Confirm real hosted pairing in Simulator with a fresh pairing session.
4. Select the paid Apple Developer team in Xcode.
5. Register/use Release bundle ID if Apple requires registration.
6. Create the App Store Connect app record if needed.
7. Archive Release.
8. Validate archive.
9. Upload Internal TestFlight build.
10. Install via TestFlight on physical iPhone.
11. Perform real QR pairing.
12. Perform real manual-code pairing.
13. Display real quota.
14. Verify pairing across relaunch.
15. Verify foreground 60-second refresh.
16. Verify pull-to-refresh.
17. Verify offline cached display and reconnect recovery.

Hosted pairing must be retested after the UUID casing correction before I-06B
or end-to-end success can be claimed.
