import {
  RELAY_TEST_UNAVAILABLE_REASON,
  resolveRelayTestConfig,
} from "./relay_test_config.ts";

function assert(condition: unknown, message = "assertion failed"): asserts condition {
  if (!condition) throw new Error(message);
}

const localUrl = "postgresql://relay:local-secret@127.0.0.1:55432/postgres";
const remoteUrl = "postgresql://relay:private-secret@db.invalid:6543/postgres";
const localPepper = "local-test-pepper-value-at-least-32-bytes";
const remotePepper = "hosted-runtime-pepper-that-must-not-be-used";

Deno.test("relay database tests require complete configuration", () => {
  assert(resolveRelayTestConfig({}) === undefined);
  assert(RELAY_TEST_UNAVAILABLE_REASON.includes("local database"));
});

Deno.test("relay database tests accept loopback runtime fallback", () => {
  const config = resolveRelayTestConfig({
    FLIGHTMARGIN_RELAY_DATABASE_URL: localUrl,
    FLIGHTMARGIN_RELAY_PEPPER: localPepper,
  });
  assert(config?.databaseUrl === localUrl);
  assert(config?.pepper === localPepper);
});

Deno.test("relay database tests prefer explicit loopback test variables", () => {
  const config = resolveRelayTestConfig({
    FLIGHTMARGIN_RELAY_TEST_DATABASE_URL: localUrl,
    FLIGHTMARGIN_RELAY_TEST_PEPPER: localPepper,
    FLIGHTMARGIN_RELAY_DATABASE_URL: remoteUrl,
    FLIGHTMARGIN_RELAY_PEPPER: remotePepper,
  });
  assert(config?.databaseUrl === localUrl);
  assert(config?.pepper === localPepper);
});

Deno.test("relay database tests reject non-loopback URLs without disclosure", () => {
  for (
    const databaseUrl of [
      remoteUrl,
      "postgresql://relay:secret@localhost.example/postgres",
      "postgresql://relay:secret@[::2]/postgres",
    ]
  ) {
    assert(
      resolveRelayTestConfig({
        FLIGHTMARGIN_RELAY_TEST_DATABASE_URL: databaseUrl,
        FLIGHTMARGIN_RELAY_TEST_PEPPER: localPepper,
      }) === undefined,
    );
  }
  assert(!RELAY_TEST_UNAVAILABLE_REASON.includes("db.invalid"));
  assert(!RELAY_TEST_UNAVAILABLE_REASON.includes("private-secret"));
  assert(!RELAY_TEST_UNAVAILABLE_REASON.includes(remotePepper));
});

Deno.test("relay database tests never pair a rejected runtime URL and pepper", () => {
  assert(
    resolveRelayTestConfig({
      FLIGHTMARGIN_RELAY_DATABASE_URL: remoteUrl,
      FLIGHTMARGIN_RELAY_PEPPER: remotePepper,
    }) === undefined,
  );
  assert(
    resolveRelayTestConfig({
      FLIGHTMARGIN_RELAY_TEST_DATABASE_URL: localUrl,
      FLIGHTMARGIN_RELAY_DATABASE_URL: remoteUrl,
      FLIGHTMARGIN_RELAY_PEPPER: remotePepper,
    }) === undefined,
  );
});
