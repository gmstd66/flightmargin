# FlightMargin Internal TestFlight preparation

## Build identity

- Product: FlightMargin
- Platform: iOS
- Minimum OS: iOS 17.0
- Debug bundle: `com.gmstd.flightmargin.dev`
- Release bundle: `io.github.gmstd66.flightmargin`
- Widget Release bundle: `io.github.gmstd66.flightmargin.widget`
- App Group: `group.io.github.gmstd66.flightmargin`
- Marketing version: `0.1.0`
- Initial build: `1`
- Distribution target: Internal TestFlight only for the first physical-phone demo

Release app signing remains manual: `iPhone Distribution`, team `JL2WCD3FDQ`,
and profile `FlightMargin App Store`. Debug remains automatic and does not use
that profile. The widget Release target is manual but intentionally has no
fabricated profile specifier until its Apple-side profile exists.

No public App Store release is authorized. No external TestFlight testing is
authorized yet. This COXON task does not contact Apple or App Store Connect and
does not upload a TestFlight or App Store build.

## Current physical result and pending correction retest

Build 0.1.0 (1) installed through Internal TestFlight on a physical iPhone,
paired successfully with the hosted relay, displayed real quota, and preserved
pairing across relaunch. Relaunch could show offline until pull-to-refresh due
to competing launch/active foreground-loop starts. I-06B makes loop startup
idempotent; build 2 must retest relaunch before the correction is closed.

## Widget Apple Developer work still required

The following steps have not been performed by this source task:

1. Create App Group `group.io.github.gmstd66.flightmargin`.
2. Enable it for `io.github.gmstd66.flightmargin`.
3. Register `io.github.gmstd66.flightmargin.widget`.
4. Enable the same App Group for that widget identifier.
5. Regenerate `FlightMargin App Store` with the new App Group entitlement.
6. Create a widget profile, suggested name `FlightMargin Widget App Store`.

Existing Apple-side registration for the first app build includes:

- Apple Developer App ID `FlightMargin iOS` is registered as the explicit
  identifier `io.github.gmstd66.flightmargin`.
- The FlightMargin iOS app record exists in App Store Connect.
- The internal TestFlight group `FlightMargin Internal` exists.
- The owner's App Store Connect account has been added as an internal tester.

The repository now contains the approved AppIcon. No public App Store
submission or external TestFlight testing is authorized.

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

1. Pull `dev/ios-testflight-demo` on Mac and open with Xcode 27.1.
2. Complete the App Group/widget identifier/profile steps above.
3. Assign the new widget profile without changing the app's known-good Release
   signing or applying App Store profiles to Debug.
4. Run all native XCTest and Simulator build/test validation.
5. Manually increment build 1 to build 2.
6. Archive, validate, and upload Internal TestFlight build 2.
7. On the physical iPhone, verify paired relaunch immediately reconnects,
   foreground 60-second refresh, pull-to-refresh, and cached offline recovery.
8. Add the medium widget and validate current, stale, offline/cached, empty,
   history graph, reset context, and tap-to-open states.
