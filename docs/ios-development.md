# FlightMargin iOS development

## Status and boundaries

I-06A provides the native SwiftUI source, Xcode project, and XCTest suite for
the first FlightMargin iPhone companion. On the user's Mac, Xcode 16.4 opened
the generated project, an iPhone 16 Pro Simulator build succeeded, and the app
launched into the expected first-run unpaired UI. The first Product > Test run
then exposed a test-harness portability issue: Apple Foundation presented an
intercepted POST body through `httpBodyStream` rather than `httpBody`. The
shared XCTest support now accepts either representation without changing
production networking. Native XCTest, Keychain, and URL-opening validation
remain pending a Mac rerun after this fix; COXON cannot compile or execute
iOS XCTest.

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
git switch dev/ios-client
git pull --ff-only origin dev/ios-client
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

Treat compile warnings and every XCTest failure as an I-06A finding to return
to COXON. Do not report the native gate complete until both commands pass.

## A. I-06A Simulator, mock, and native checks

Run or install the app from Xcode and verify:

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

Do not create a real hosted pairing during I-06A. Manual-code network behavior
and successful deep-link behavior are covered by mocked URLSession/XCTest;
real hosted end-to-end validation belongs to I-06B.

## B. I-06B hosted relay and physical-iPhone plan

I-06B should use a real FlightMargin desktop/Linux host and the already-live
hosted relay:

1. Configure development signing on the Mac and install the app on a physical
   iPhone.
2. Enable Mobile Relay on the real host and confirm it has uploaded current
   quota.
3. Create a fresh pairing QR/manual code on the host.
4. Scan the QR with Camera, verify the `flightmargin://pair/v1` link opens
   FlightMargin, claim the real pairing, and retrieve real latest quota.
5. Locally reset, create a new session, and repeat with manual-code pairing.
6. Relaunch the app and the host; verify stable pairing and refreshed quota.
7. Disable connectivity, confirm cached quota remains with an offline/stale
   indicator, reconnect, and confirm recovery without re-pairing.
8. Verify foreground 60-second refresh, pull-to-refresh, background pause, and
   no overlapping requests.
9. Confirm no OpenAI/Codex credential, prompt, transcript, source, agent output,
   username, filesystem path, or remote history reaches the iPhone or relay.

Physical-device validation does not authorize TestFlight, App Store work,
production signing decisions, backend changes, or publication.
