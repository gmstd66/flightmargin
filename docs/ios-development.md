# FlightMargin iOS development

## Status and boundaries

I-06A is complete. It provides the native SwiftUI source, Xcode project, and
XCTest suite for the first FlightMargin iPhone companion. On the user's Mac,
Xcode 16.4 opened the project, an iPhone 16 Pro Simulator build succeeded, the
app launched, and the final native XCTest rerun passed all 19 tests. The
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

There is no TestFlight or App Store build, production signing configuration,
or public iPhone application. The development bundle identifier is
`com.gmstd.flightmargin.dev`; choose the final production identifier before
TestFlight or App Store work. I-06A does not change the relay v1 contract and
does not add a Supabase SDK, account, login, analytics, or third-party runtime
dependency.

## Get the branch on the Mac

After the user has pushed the reviewed branch from COXON:

```bash
git fetch origin
git switch develop
git pull --ff-only origin develop
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

## B. I-06B hosted relay and physical-iPhone plan

I-06B is the next milestone and should use a real FlightMargin desktop/Linux
host and the already-live hosted relay:

1. Configure development signing on the Mac and install the app on a physical
   iPhone.
2. Enable Mobile Relay on the real host and confirm a real quota upload.
3. Create a real pairing QR/manual session on the host.
4. Scan the QR with Camera, verify the `flightmargin://pair/v1` link opens
   FlightMargin, claim the real pairing, and retrieve real latest quota.
5. Locally reset, create a new session, and repeat with manual-code pairing.
6. Relaunch the app and verify that pairing persists and real quota remains
   available.
7. Disable connectivity, confirm cached quota remains with an offline/stale
   indicator, reconnect, and confirm recovery without re-pairing.
8. Verify foreground 60-second refresh and pull-to-refresh; also confirm the
   expected background pause and no overlapping requests.
9. Confirm no OpenAI/Codex credential, prompt, transcript, source, agent output,
   username, filesystem path, or remote history reaches the iPhone or relay.

Physical-device validation does not authorize TestFlight, App Store work,
production signing decisions, backend changes, or publication.
