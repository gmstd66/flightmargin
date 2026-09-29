import vectors from "../../../../tests/fixtures/mobile-relay-crypto-vectors.json" with {
  type: "json",
};
import { createHandler } from "../router.ts";
import {
  AuthenticationFailed,
  type HostRegistration,
  type PairingClaim,
  PairingFailed,
  type PairingMethod,
  type PairingResult,
  type ParsedCredential,
  type QuotaReport,
  type RateLimitResult,
  type RelayRepository,
} from "../types.ts";

function assertEquals(actual: unknown, expected: unknown): void {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(
      `Expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`,
    );
  }
}

class FakeRepository implements RelayRepository {
  rateCalls: Array<[string, string, number, number]> = [];
  rateCount = 0;
  stale = false;
  authFailure = false;
  pairingFailure = false;
  registration?: HostRegistration;
  claim?: PairingClaim;
  method?: PairingMethod;

  rateLimit(
    action: "host-registration" | "pairing-claim",
    digest: string,
    seconds: number,
    limit: number,
  ): Promise<RateLimitResult> {
    this.rateCalls.push([action, digest, seconds, limit]);
    this.rateCount += 1;
    return Promise.resolve({ allowed: this.rateCount <= limit, retryAfter: 42 });
  }
  registerHost(value: HostRegistration): Promise<boolean> {
    this.registration = value;
    return Promise.resolve(true);
  }
  putQuota(_credential: ParsedCredential, _report: QuotaReport): Promise<boolean> {
    if (this.authFailure) throw new AuthenticationFailed();
    return Promise.resolve(!this.stale);
  }
  createPairing(_credential: ParsedCredential): Promise<PairingResult> {
    if (this.authFailure) throw new AuthenticationFailed();
    return Promise.resolve({
      pairingToken: vectors.pairing_token,
      manualCode: vectors.manual_code,
      expiresAt: "2026-09-29T20:05:00.000Z",
    });
  }
  claimPairing(
    claim: PairingClaim,
    _credential: ParsedCredential,
    method: PairingMethod,
  ): Promise<string> {
    if (this.pairingFailure) throw new PairingFailed();
    this.claim = claim;
    this.method = method;
    return Promise.resolve("11111111-1111-4111-8111-111111111111");
  }
  getQuota(_credential: ParsedCredential): Promise<Record<string, unknown>> {
    if (this.authFailure) throw new AuthenticationFailed();
    return Promise.resolve({ api_version: 1, host: {}, quota: null });
  }
}

const pepper = new TextEncoder().encode(vectors.pepper);
const registration = {
  host_id: "11111111-1111-4111-8111-111111111111",
  display_name: "Test host",
  platform: "linux",
  app_version: "test",
  credential: vectors.host_credential,
};
const quota = {
  schema_version: 1,
  sampled_at: "2026-09-29T20:00:00Z",
  five_hour_used: 42.5,
  weekly_used: null,
};
const claim = {
  pairing_token: vectors.pairing_token,
  device_id: "44444444-4444-4444-8444-444444444444",
  display_name: "Test iPhone",
  platform: "ios",
  credential: vectors.device_credential,
};

function jsonRequest(
  path: string,
  method: string,
  body: unknown,
  headers = {},
): Request {
  return new Request(`https://relay.example${path}`, {
    method,
    headers: { "content-type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
}

Deno.test("health is liveness-only and supports the Supabase function prefix", async () => {
  const handler = createHandler();
  const response = await handler(new Request("https://relay.example/relay-v1/health"));
  assertEquals(response.status, 200);
  assertEquals(await response.json(), { status: "ok" });
});

Deno.test("strict unsupported path and method handling", async () => {
  const handler = createHandler({ repository: new FakeRepository(), pepper });
  assertEquals(
    (await handler(new Request("https://relay.example/missing"))).status,
    404,
  );
  const method = await handler(new Request("https://relay.example/v1/pairings"));
  assertEquals(method.status, 405);
  assertEquals(method.headers.get("allow"), "POST");
});

Deno.test("registration validates and preserves v1 response semantics", async () => {
  const repository = new FakeRepository();
  const handler = createHandler({ repository, pepper });
  const response = await handler(
    jsonRequest("/v1/hosts/register", "POST", registration, {
      "cf-connecting-ip": vectors.ip,
    }),
  );
  assertEquals(response.status, 201);
  assertEquals((await response.json()).result, "registered");
  assertEquals(repository.registration?.displayName, "Test host");
  assertEquals(repository.rateCalls[0][0], "host-registration");
  assertEquals(repository.rateCalls[0][2], 3600);
  assertEquals(repository.rateCalls[0][3], 10);
});

Deno.test("JSON content type, malformed, extra, and oversized bodies are rejected", async () => {
  const handler = createHandler({ repository: new FakeRepository(), pepper });
  const missingType = await handler(
    new Request("https://relay.example/v1/hosts/register", {
      method: "POST",
      body: JSON.stringify(registration),
    }),
  );
  assertEquals(missingType.status, 415);
  const extra = await handler(jsonRequest("/v1/hosts/register", "POST", {
    ...registration,
    unexpected: true,
  }));
  assertEquals(extra.status, 422);
  const malformed = await handler(
    new Request("https://relay.example/v1/hosts/register", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{",
    }),
  );
  assertEquals(malformed.status, 422);
  const oversized = await handler(jsonRequest("/v1/hosts/register", "POST", {
    padding: "x".repeat(17_000),
  }));
  assertEquals(oversized.status, 413);
});

Deno.test("host auth and monotonic quota result semantics", async () => {
  const repository = new FakeRepository();
  const handler = createHandler({ repository, pepper });
  const unauthorized = await handler(jsonRequest("/v1/quota", "PUT", quota));
  assertEquals(unauthorized.status, 401);
  const headers = { authorization: `Bearer ${vectors.host_credential}` };
  assertEquals(
    (await handler(jsonRequest("/v1/quota", "PUT", quota, headers))).status,
    200,
  );
  repository.stale = true;
  const stale = await handler(jsonRequest("/v1/quota", "PUT", quota, headers));
  assertEquals((await stale.json()).result, "stale");
});

Deno.test("device auth and safe generic authentication errors", async () => {
  const repository = new FakeRepository();
  repository.authFailure = true;
  const handler = createHandler({ repository, pepper });
  const response = await handler(
    new Request("https://relay.example/v1/quota", {
      headers: { authorization: `Bearer ${vectors.device_credential}` },
    }),
  );
  assertEquals(response.status, 401);
  assertEquals(await response.json(), { detail: "Invalid or revoked credential" });
});

Deno.test("pairing creation and QR/manual claims retain v1 shapes", async () => {
  const repository = new FakeRepository();
  const handler = createHandler({ repository, pepper });
  const pairing = await handler(
    new Request("https://relay.example/v1/pairings", {
      method: "POST",
      headers: { authorization: `Bearer ${vectors.host_credential}` },
    }),
  );
  assertEquals(pairing.status, 201);
  assertEquals((await pairing.json()).manual_code, vectors.manual_code);
  const qr = await handler(jsonRequest("/v1/pairings/claim", "POST", claim));
  assertEquals(qr.status, 200);
  assertEquals(repository.method && "token" in repository.method, true);
  const manual = await handler(jsonRequest("/v1/pairings/claim", "POST", {
    ...claim,
    pairing_token: undefined,
    manual_code: vectors.manual_code,
  }));
  assertEquals(manual.status, 200);
  assertEquals(repository.method && "manualCode" in repository.method, true);
});

Deno.test("pairing failure and internal failure responses do not expose secrets", async () => {
  const repository = new FakeRepository();
  repository.pairingFailure = true;
  const handler = createHandler({ repository, pepper });
  const pairing = await handler(jsonRequest("/v1/pairings/claim", "POST", claim));
  assertEquals(pairing.status, 400);
  assertEquals(await pairing.json(), { detail: "Pairing could not be completed" });

  repository.pairingFailure = false;
  repository.claimPairing = () => {
    throw new Error(`private ${vectors.pairing_token}`);
  };
  const internal = await handler(jsonRequest("/v1/pairings/claim", "POST", claim));
  assertEquals(internal.status, 500);
  assertEquals(await internal.json(), { detail: "Internal server error" });
});

Deno.test("public rate limits return 429 after both documented thresholds", async () => {
  const repository = new FakeRepository();
  const handler = createHandler({ repository, pepper });
  for (let index = 0; index < 10; index += 1) {
    assertEquals(
      (await handler(jsonRequest("/v1/hosts/register", "POST", registration))).status,
      201,
    );
  }
  const limited = await handler(
    jsonRequest("/v1/hosts/register", "POST", registration),
  );
  assertEquals(limited.status, 429);
  assertEquals(limited.headers.get("retry-after"), "42");

  const claimRepository = new FakeRepository();
  const claimHandler = createHandler({ repository: claimRepository, pepper });
  for (let index = 0; index < 20; index += 1) {
    assertEquals(
      (await claimHandler(jsonRequest("/v1/pairings/claim", "POST", claim))).status,
      200,
    );
  }
  const claimLimited = await claimHandler(
    jsonRequest("/v1/pairings/claim", "POST", claim),
  );
  assertEquals(claimLimited.status, 429);
  assertEquals(claimRepository.rateCalls[0][2], 300);
  assertEquals(claimRepository.rateCalls[0][3], 20);
});
