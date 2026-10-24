# FlightMargin iOS development

## Status and boundaries

I-06A is complete. It provides the native SwiftUI source, Xcode project, and
XCTest suite for the first FlightMargin iPhone companion. On the user's Mac,
Xcode 16.4 opened the project, an iPhone 16 Pro Simulator build succeeded, the
app launched, and the latest native XCTest baseline passed all 21 tests. The
earlier Apple Foundation request-body portability issue and stale Supabase
Edge Function path assertions are fixed without changing production
networking or the relay v1 contract.

Simulator validation also passed for warm and cold
`flightmargin://pair/v1` routing through a loopback-only Debug relay override.
The raw pairing token was not shown, and the unavailable-relay error was
sanitized. A local mock relay then proved successful manual pairing, claim,
authenticated quota retrieval, and the complete dashboard presentation.
Keychain identity persisted across full app termination and relaunch: two
consecutive claims produced the same SHA-256 fingerprint of the device ID and
credential without printing either raw value. Local reset returned the app to
the unpaired state, and the next pairing produced a different fingerprint,
confirming deletion and rotation of the Keychain identity.

With the mock relay stopped, pull-to-refresh preserved pairing, cached quota,
and dashboard state while showing the sanitized message, **Unable to refresh.
Showing the last available quota.** Restarting the same relay and refreshing
cleared the banner, retained pairing, and advanced the app refresh timestamp
without re-pairing. The intentionally old synthetic sample independently
showed the expected stale indication. Cleanup stopped the mock relay and
removed the Simulator endpoint override. No hosted Supabase operation occurred
during I-06A validation.

Internal TestFlight build 0.1.0 (2) is the accepted physical-device checkpoint
and completes I-06B. On a real iPhone it installed and launched, paired with
the hosted relay, displayed real quota, retained pairing across relaunch, and
performed the corrected automatic foreground reconnect without requiring a
manual refresh. Pull-to-refresh, 60-second foreground refresh,
background/foreground resume, cached offline/stale presentation, and recovery
without re-pairing all passed. Release signing is intentionally manual with team
`JL2WCD3FDQ`, bundle `io.github.gmstd66.flightmargin`, identity
`iPhone Distribution`, and profile `FlightMargin App Store`; Debug remains
independent from App Store profiles. No external TestFlight testing or public
App Store submission/release is authorized.

I-06B hosted diagnostics confirmed that the COXON host relay was **Connected**
to the production relay endpoint and that the Simulator had
internet/hosted-relay connectivity. An earlier source audit corrected
pairing-claim `device_id` wire encoding to canonical lowercase while retaining
`UUID` internally; credential storage, pairing semantics, and relay v1 were
unchanged.

Later captured Simulator traffic proved that a previously entered full-length
manual code was actually transmitted after the user entered a fresh code. The
SwiftUI sheet retained its ten valid characters after a failed attempt, so
`ManualCode.displayValue()` discarded newly appended characters at its
ten-character limit and left the stale value in place. A controlled direct
hosted claim independently succeeded, isolating the defect to the iOS manual
input path. `PairingView` now clears its sheet-local code on manual-claim
failure before presenting the existing sanitized sheet-local error. Successful
manual pairing and app-level QR/deep-link error ownership are unchanged.
Physical validation exposed a lifecycle race: both `launch()` and the active
scene callback started foreground refresh. The second start canceled the task
performing the immediate fetch, then its replacement returned because the
serialized refresh was still marked active and slept for 60 seconds. Startup
is now idempotent while a periodic task exists; stop cancels and clears it.
Pull-to-refresh, cached/offline behavior, persistence, Keychain identity, and
the relay contract are unchanged. Build 2 passed the corrected physical
relaunch and complete I-06B validation described above.

I-07A adds `FlightMarginWidget`, a medium-only iOS 17 WidgetKit extension. The
main app stores only a sanitized `WidgetSnapshot` in App Group
`group.io.github.gmstd66.flightmargin`: schema and timestamps, optional host
display name, five-hour/weekly used and remaining values and reset dates,
optional plan type, current/offline state, and at most 72 timestamped
five-hour utilization samples. Exact duplicate final samples are suppressed.
The widget reads that file, makes no network request, has no Keychain or relay
client source, and uses an honest 15-minute timeline request while displaying
fresh/stale/offline status because WidgetKit controls actual scheduling.
Credentials, pairing values, device identifiers, bearer tokens, raw relay
bodies, prompts, transcripts, source code, and agent output never enter the
App Group. I-07A is complete: on the physical iPhone the widget was available,
showed current five-hour and weekly utilization and accumulating local history,
handled fresh/stale/offline-cached states, reflected refreshed app data under
WidgetKit scheduling, and opened FlightMargin when tapped.

Apple-side configuration is complete for this checkpoint. App Group
`group.io.github.gmstd66.flightmargin` exists and is enabled for both the main
App ID and widget App ID `io.github.gmstd66.flightmargin.widget`. The main
profile `FlightMargin App Store` was regenerated, and widget profile
`FlightMargin Widget App Store` was created. Widget Release signing is manual
with `iPhone Distribution`, team `JL2WCD3FDQ`, its widget bundle ID, and that
widget profile.

The privacy-manifest audit found only direct `UserDefaults` required-reason
API use and declares `CA92.1`; no tracking or collected-data entry is declared.
`ITSAppUsesNonExemptEncryption` is `NO` because the app currently relies on
Apple `URLSession`/HTTPS and ships no proprietary or third-party cryptography.
Revisit that declaration if crypto behavior or dependencies change. See
`docs/ios-testflight.md` for the Internal TestFlight handoff.

## Get the branch on the Mac

After the user has pushed the reviewed branch from COXON:

```bash
git fetch origin
git switch dev/ios-testflight-demo
git pull --ff-only origin dev/ios-testflight-demo
open ios/FlightMargin.xcodeproj
```

In Xcode, select the shared `FlightMargin` scheme and any installed iPhone
Simulator running iOS 17 or newer. A development team should not be needed for
Simulator builds. List the project and available devices from Terminal:

```bash
xcodebuild -list -project ios/FlightMargin.xcodeproj
xcrun simctl list devices available
```

Choose an available iPhone Simulator UUID from the second command, then use it
without assuming a future simulator model:

```bash
SIMULATOR_UDID="<available-simulator-uuid>"
xcrun simctl boot "$SIMULATOR_UDID" 2>/dev/null || true
open -a Simulator

xcodebuild build \
  -project ios/FlightMargin.xcodeproj \
  -scheme FlightMargin \
  -destination "platform=iOS Simulator,id=$SIMULATOR_UDID" \
  CODE_SIGNING_ALLOWED=NO

xcodebuild test \
  -project ios/FlightMargin.xcodeproj \
  -scheme FlightMargin \
  -destination "platform=iOS Simulator,id=$SIMULATOR_UDID" \
  CODE_SIGNING_ALLOWED=NO
```

These commands passed for the I-06A closure on Xcode 16.4 with an iPhone 16
Pro Simulator. Treat future compile warnings or XCTest failures as regressions.

## A. I-06A Simulator, mock, and native checks (complete)

The completed validation covered:

1. A fresh install opens on the unpaired FlightMargin screen with no account
   or login language.
2. **Enter pairing code** uppercases lowercase input, removes spaces, inserts
   the hyphen, and rejects malformed or forbidden Crockford characters.
3. Pairing shows progress and sanitized failures; no credential or raw pairing
   token appears in UI, the Xcode console, or diagnostics.
4. The XCTest suite passes, including generated device credentials, in-memory
   secure storage, native Keychain round-trip, endpoint policy, mocked exact
   claim/quota requests, lost-response identity reuse, quota caching,
   serialized refresh, and reset.
5. With mocked responses, the dashboard shows host, used/remaining gauges,
   reset times, plan, optional credits, sample time, refresh time, and stale or
   offline state. Pull to refresh and confirm that a failure leaves the prior
   quota visible.
6. Relaunch and confirm the Keychain identity is stable. Use **Reset pairing
   on this iPhone**, accept the warning, and confirm the app returns to the
   unpaired screen. Reset is local only and does not revoke the relay device.

The Debug app supports an explicit `FLIGHTMARGIN_RELAY_ENDPOINT` process
environment override. Release builds ignore it. The override still requires
HTTPS unless the host is syntactically `localhost`, `127.0.0.0/8`, or `::1`.
For safe URL-routing checks without hosted contact, point the Simulator app at
an intentionally unused Mac loopback port before launch:

```bash
xcrun simctl spawn booted launchctl setenv \
  FLIGHTMARGIN_RELAY_ENDPOINT http://127.0.0.1:18096
```

Use this syntactically valid, non-live test token (it is not a credential for
any relay record):

```bash
PAIR_URL='flightmargin://pair/v1?token=fmp1.33333333-3333-4333-8333-333333333333.UFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFA'
```

Warm handling, with the app already open:

```bash
xcrun simctl openurl booted "$PAIR_URL"
```

Cold handling:

```bash
xcrun simctl terminate booted com.gmstd.flightmargin.dev
xcrun simctl openurl booted "$PAIR_URL"
```

Both paths should open FlightMargin, enter pairing progress, then show a
sanitized unavailable result because nothing listens on port 18096. They must
reuse the same Keychain identity. Clear the injected environment afterward:

```bash
xcrun simctl spawn booted launchctl unsetenv FLIGHTMARGIN_RELAY_ENDPOINT
```

I-06A did not create a hosted pairing or contact hosted Supabase. Real hosted
end-to-end validation belongs to I-06B.

## B. I-06B physical-iPhone correction and retest (complete)

Internal TestFlight build 0.1.0 (2) passed on a physical iPhone:

1. Installation, launch, real hosted manual pairing, quota display, and pairing
   persistence passed.
2. Relaunch performed the corrected automatic foreground reconnect without
   pull-to-refresh.
3. Pull-to-refresh, 60-second foreground refresh, and background/foreground
   resume passed. This does not claim background 60-second execution.
4. Cached data remained available with appropriate offline/stale presentation,
   and connectivity recovery succeeded without re-pairing.

## C. I-07A widget Apple-side setup and validation (complete)

The App Group, both entitled App IDs, regenerated main profile, and widget
profile are complete as recorded above. The medium widget passed physical
iPhone checks for five-hour/weekly display, bounded local history graph,
freshness, stale/offline-cached presentation, propagation of refreshed app data
under WidgetKit scheduling, App Group sharing, and tap-to-open.

The user has an active paid Apple Developer Program membership, so Internal
TestFlight is the intended remote-Mac path for the first physical-phone demo.
The explicit App ID, FlightMargin App Store Connect app record, internal
TestFlight group `FlightMargin Internal`, and internal tester enrollment are
complete. Build 0.1.0 (2) is the accepted internal physical checkpoint. No
external TestFlight testing or public App Store submission/release is
authorized. Backend changes and publication remain out of scope.
