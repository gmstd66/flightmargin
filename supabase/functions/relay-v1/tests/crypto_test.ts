import vectors from "../../../../tests/fixtures/mobile-relay-crypto-vectors.json" with {
  type: "json",
};
import {
  credentialDigest,
  normalizeManualCode,
  pairingManualDigest,
  pairingQrDigest,
  parseCredential,
  parsePairingToken,
  rateLimitIdentityDigest,
} from "../crypto.ts";

function assertEquals(actual: unknown, expected: unknown): void {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(
      `Expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`,
    );
  }
}

Deno.test("credential parsing and contextual HMAC match Python vectors", async () => {
  const pepper = new TextEncoder().encode(vectors.pepper);
  assertEquals(
    await credentialDigest(parseCredential(vectors.host_credential, "host"), pepper),
    vectors.host_digest,
  );
  assertEquals(
    await credentialDigest(
      parseCredential(vectors.device_credential, "device"),
      pepper,
    ),
    vectors.device_digest,
  );
});

Deno.test("pairing and rate-limit HMAC contexts match shared vectors", async () => {
  const pepper = new TextEncoder().encode(vectors.pepper);
  assertEquals(
    await pairingQrDigest(parsePairingToken(vectors.pairing_token), pepper),
    vectors.pairing_qr_digest,
  );
  assertEquals(
    await pairingManualDigest(normalizeManualCode(vectors.manual_code), pepper),
    vectors.pairing_manual_digest,
  );
  assertEquals(
    await rateLimitIdentityDigest(vectors.ip, pepper),
    vectors.rate_limit_digest,
  );
});

Deno.test("credential and pairing parsers reject noncanonical values", () => {
  for (
    const action of [
      () => parseCredential(vectors.host_credential.replace("fmh1", "fmd1"), "host"),
      () => parseCredential(vectors.host_credential.toUpperCase(), "host"),
      () => parsePairingToken(`${vectors.pairing_token}=`),
      () => normalizeManualCode("O1234-56789"),
    ]
  ) {
    let rejected = false;
    try {
      action();
    } catch {
      rejected = true;
    }
    assertEquals(rejected, true);
  }
});
