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
- Accepted checkpoint: `0.1.0 (2)`
- Distribution target: Internal TestFlight only for the first physical-phone demo

Release app signing remains manual: `iPhone Distribution`, team `JL2WCD3FDQ`,
bundle `io.github.gmstd66.flightmargin`, and profile
`FlightMargin App Store`. Widget Release signing is also manual:
`iPhone Distribution`, team `JL2WCD3FDQ`, bundle
`io.github.gmstd66.flightmargin.widget`, and profile
`FlightMargin Widget App Store`. Debug remains independent from App Store
profiles.

No public App Store release is authorized. No external TestFlight testing is
authorized yet. This COXON task does not contact Apple or App Store Connect and
does not upload a TestFlight or App Store build.

## Accepted physical result

Internal TestFlight build 0.1.0 (2) installed and launched on a physical iPhone
and is the accepted checkpoint. I-06B is complete: real hosted manual pairing,
quota display, pairing persistence, corrected automatic reconnect on relaunch,
pull-to-refresh, 60-second foreground refresh, background/foreground resume,
cached offline/stale presentation, and recovery without re-pairing all passed.
This does not claim background 60-second execution.

I-07A is also complete. The medium Home Screen widget displayed current
five-hour and weekly utilization and its bounded local five-hour history graph,
handled fresh/stale/offline-cached states, reflected app refreshes under
WidgetKit scheduling, shared data through the App Group, and opened
FlightMargin when tapped. No stronger update cadence than WidgetKit provides
is claimed.

## Apple Developer configuration

Apple-side configuration is complete for this checkpoint:

- App Group `group.io.github.gmstd66.flightmargin` exists.
- Main App ID `io.github.gmstd66.flightmargin` has the App Group entitlement.
- Widget App ID `io.github.gmstd66.flightmargin.widget` exists and has the same
  App Group entitlement.
- Main profile `FlightMargin App Store` was regenerated.
- Widget profile `FlightMargin Widget App Store` exists.

Existing Apple-side registration for the first app build includes:

- Apple Developer App ID `FlightMargin iOS` is registered as the explicit
  identifier `io.github.gmstd66.flightmargin`.
- The FlightMargin iOS app record exists in App Store Connect.
- The internal TestFlight group `FlightMargin Internal` exists.
- The owner's App Store Connect account has been added as an internal tester.

The repository contains the approved AppIcon. No public App Store
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

The repository contains the approved iOS AppIcon and the application target is
configured to use it. Do not change it as part of checkpoint closure.

## Completed native evidence

Xcode 27.1 native tests passed on the Mac before the archive. The accepted
build-2 app and widget results above were validated through Internal TestFlight
on the physical iPhone. They are external validation evidence and are not
rerun on COXON.

No networking, pairing, credentials, device IDs, tokens, prompts, transcripts,
source code, or agent output are stored in the widget shared snapshot.
