import { Pool } from "pg";
import { randomSecret, rateLimitIdentityDigest } from "../crypto.ts";
import { createPgClient, PostgresRelayRepository } from "../db.ts";
import { createHandler } from "../router.ts";
import {
  RELAY_TEST_UNAVAILABLE_REASON,
  relayTestConfigFromEnvironment,
} from "./relay_test_config.ts";

function assert(condition: unknown, message = "assertion failed"): asserts condition {
  if (!condition) throw new Error(message);
}

function assertEquals(actual: unknown, expected: unknown): void {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(
      `Expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`,
    );
  }
}

const relayTestConfig = relayTestConfigFromEnvironment();
const databaseUrl = relayTestConfig?.databaseUrl;
const pepperValue = relayTestConfig?.pepper;
const canIntegrate = relayTestConfig !== undefined;
const skippedSuffix = canIntegrate ? "" : ` [${RELAY_TEST_UNAVAILABLE_REASON}]`;

function credential(kind: "host" | "device", id = crypto.randomUUID()): string {
  return `${kind === "host" ? "fmh1" : "fmd1"}.${id}.${randomSecret()}`;
}

function registration(hostId: string, hostCredential: string) {
  return {
    host_id: hostId,
    display_name: "Deno integration host",
    platform: "linux",
    app_version: "test",
    credential: hostCredential,
  };
}

function quota(sampledAt: Date, used: number) {
  return {
    schema_version: 1,
    sampled_at: sampledAt.toISOString(),
    five_hour_used: used,
    five_hour_reset_at: null,
    weekly_used: 70,
    weekly_reset_at: null,
    plan_type: "plus",
    reset_credits_available: 2,
    credits_balance: 4.5,
    spend_control_reached: false,
    rate_limit_reached_type: null,
    collector_state: "ok",
    collector_message_code: null,
  };
}

function claim(tokenOrCode: { pairing_token?: string; manual_code?: string }) {
  return {
    ...tokenOrCode,
    device_id: crypto.randomUUID(),
    display_name: "Integration iPhone",
    platform: "ios",
    credential: credential("device"),
  };
}

function request(
  path: string,
  method: string,
  body?: unknown,
  token?: string,
  ip?: string,
) {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["content-type"] = "application/json";
  if (token) headers.authorization = `Bearer ${token}`;
  if (ip) headers["cf-connecting-ip"] = ip;
  return new Request(`https://relay.example${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

Deno.test({
  name:
    "PostgreSQL relay supports registration, auth, quota, pairing, retry, and revocation" +
    skippedSuffix,
  ignore: !canIntegrate,
  sanitizeResources: false,
  async fn() {
    const pepper = new TextEncoder().encode(pepperValue!);
    const pool = new Pool({ connectionString: databaseUrl!, max: 1 });
    const sql = createPgClient(pool);
    const repository = new PostgresRelayRepository(pepper, sql);
    const handler = createHandler({ repository, pepper });
    const hostIds: string[] = [];
    const testIps = [
      "192.0.2.101",
      "192.0.2.102",
      "192.0.2.103",
      "192.0.2.104",
      "192.0.2.105",
    ];
    try {
      const hostId = crypto.randomUUID();
      hostIds.push(hostId);
      const hostCredential = credential("host");
      const payload = registration(hostId, hostCredential);
      const registered = await handler(
        request("/v1/hosts/register", "POST", payload, undefined, "192.0.2.101"),
      );
      assertEquals(registered.status, 201);
      assertEquals((await registered.json()).result, "registered");
      const retry = await handler(
        request("/v1/hosts/register", "POST", payload, undefined, "192.0.2.101"),
      );
      assertEquals((await retry.json()).result, "already_registered");

      const now = new Date();
      const accepted = await handler(
        request("/v1/quota", "PUT", quota(now, 61.5), hostCredential),
      );
      assertEquals((await accepted.json()).result, "accepted");
      const stale = await handler(
        request(
          "/v1/quota",
          "PUT",
          quota(new Date(now.getTime() - 60_000), 1),
          hostCredential,
        ),
      );
      assertEquals((await stale.json()).result, "stale");

      const badHostToken = hostCredential.replace(/[^.]+$/, randomSecret());
      assertEquals(
        (await handler(request("/v1/quota", "PUT", quota(now, 1), badHostToken)))
          .status,
        401,
      );

      const pairingResponse = await handler(
        request("/v1/pairings", "POST", undefined, hostCredential),
      );
      assertEquals(pairingResponse.status, 201);
      const pairing = await pairingResponse.json();
      const qrClaim = claim({ pairing_token: pairing.pairing_token });
      const paired = await handler(
        request(
          "/v1/pairings/claim",
          "POST",
          qrClaim,
          undefined,
          "192.0.2.102",
        ),
      );
      assertEquals(paired.status, 200);
      const retryClaim = await handler(
        request(
          "/v1/pairings/claim",
          "POST",
          qrClaim,
          undefined,
          "192.0.2.102",
        ),
      );
      assertEquals(retryClaim.status, 200);
      const quotaRead = await handler(
        request("/v1/quota", "GET", undefined, qrClaim.credential),
      );
      assertEquals(quotaRead.status, 200);
      assertEquals((await quotaRead.json()).quota.five_hour_used, 61.5);

      const deviceCredentialId = qrClaim.credential.split(".")[1];
      await sql`
        update relay_device_credentials set revoked_at = now()
        where id = ${deviceCredentialId}
      `;
      assertEquals(
        (await handler(request("/v1/quota", "GET", undefined, qrClaim.credential)))
          .status,
        401,
      );

      const manualPairing = await (
        await handler(request("/v1/pairings", "POST", undefined, hostCredential))
      ).json();
      const manualClaim = claim({ manual_code: manualPairing.manual_code });
      assertEquals(
        (await handler(
          request(
            "/v1/pairings/claim",
            "POST",
            manualClaim,
            undefined,
            "192.0.2.103",
          ),
        )).status,
        200,
      );

      const failedPairing = await (
        await handler(request("/v1/pairings", "POST", undefined, hostCredential))
      ).json();
      const sessionId = failedPairing.pairing_token.split(".")[1];
      const badToken = failedPairing.pairing_token.replace(/[^.]+$/, randomSecret());
      for (let attempt = 0; attempt < 5; attempt += 1) {
        assertEquals(
          (await handler(
            request(
              "/v1/pairings/claim",
              "POST",
              claim({ pairing_token: badToken }),
              undefined,
              "192.0.2.104",
            ),
          )).status,
          400,
        );
      }
      const attempts = await sql`
        select attempts from relay_pairing_sessions where id = ${sessionId}
      `;
      assertEquals(Number(attempts[0].attempts), 5);
      assertEquals(
        (await handler(
          request(
            "/v1/pairings/claim",
            "POST",
            claim({ pairing_token: failedPairing.pairing_token }),
            undefined,
            "192.0.2.104",
          ),
        )).status,
        400,
      );

      const expiredPairing = await (
        await handler(request("/v1/pairings", "POST", undefined, hostCredential))
      ).json();
      const expiredSessionId = expiredPairing.pairing_token.split(".")[1];
      await sql`
        update relay_pairing_sessions set created_at = now() - interval '10 minutes',
          expires_at = now() - interval '5 minutes' where id = ${expiredSessionId}
      `;
      assertEquals(
        (await handler(
          request(
            "/v1/pairings/claim",
            "POST",
            claim({ pairing_token: expiredPairing.pairing_token }),
            undefined,
            "192.0.2.105",
          ),
        )).status,
        400,
      );

      await sql`update relay_hosts set revoked_at = now() where id = ${hostId}`;
      assertEquals(
        (await handler(request("/v1/pairings", "POST", undefined, hostCredential)))
          .status,
        401,
      );
    } finally {
      if (hostIds.length) {
        await pool.query("delete from relay_hosts where id = any($1::uuid[])", [
          hostIds,
        ]);
      }
      const rateDigests = await Promise.all(
        testIps.map((ip) => rateLimitIdentityDigest(ip, pepper)),
      );
      await pool.query(
        "delete from relay_rate_limit_buckets where identity_digest = any($1::text[])",
        [rateDigests],
      );
      await pool.end();
    }
  },
});

Deno.test({
  name:
    "PostgreSQL public buckets are atomic, isolated HMAC identities without raw IPs" +
    skippedSuffix,
  ignore: !canIntegrate,
  sanitizeResources: false,
  async fn() {
    const pepper = new TextEncoder().encode(pepperValue!);
    const pool = new Pool({ connectionString: databaseUrl!, max: 1 });
    const sql = createPgClient(pool);
    const repository = new PostgresRelayRepository(pepper, sql);
    const concurrentPools = Array.from(
      { length: 11 },
      () => new Pool({ connectionString: databaseUrl!, max: 1 }),
    );
    const concurrentRepositories = concurrentPools.map((concurrentPool) =>
      new PostgresRelayRepository(pepper, createPgClient(concurrentPool))
    );
    const firstIp = "198.51.100.73";
    const secondIp = "203.0.113.22";
    const first = await rateLimitIdentityDigest(firstIp, pepper);
    const second = await rateLimitIdentityDigest(secondIp, pepper);
    try {
      await sql`
        delete from relay_rate_limit_buckets
        where identity_digest in (${first}, ${second})
      `;
      const results = await Promise.all(
        concurrentRepositories.map((concurrentRepository) =>
          concurrentRepository.rateLimit("host-registration", first, 3600, 10)
        ),
      );
      assertEquals(results.filter((result) => result.allowed).length, 10);
      assertEquals(results.filter((result) => !result.allowed).length, 1);
      assert(
        (await repository.rateLimit("host-registration", second, 3600, 10)).allowed,
      );
      assert((await repository.rateLimit("pairing-claim", first, 300, 20)).allowed);
      const stored = JSON.stringify(
        await sql`
        select * from relay_rate_limit_buckets
        where identity_digest in (${first}, ${second})
      `,
      );
      assert(!stored.includes(firstIp), "raw first IP was stored");
      assert(!stored.includes(secondIp), "raw second IP was stored");
      assert(stored.includes(first));
      assert(stored.includes(second));
    } finally {
      await sql`
        delete from relay_rate_limit_buckets
        where identity_digest in (${first}, ${second})
      `;
      await Promise.all(concurrentPools.map((concurrentPool) => concurrentPool.end()));
      await pool.end();
    }
  },
});

Deno.test({
  name: "node-postgres executes and rolls back a multi-query transaction" +
    skippedSuffix,
  ignore: !canIntegrate,
  sanitizeResources: false,
  async fn() {
    const pool = new Pool({ connectionString: databaseUrl!, max: 1 });
    const sql = createPgClient(pool);
    const hostId = crypto.randomUUID();
    let rolledBack = false;
    try {
      try {
        await sql.begin(async (transaction) => {
          await transaction`set local statement_timeout = '5s'`;
          await transaction`
            insert into relay_hosts (id, display_name, platform, app_version)
            values (${hostId}, ${"Rollback host"}, ${"linux"}, ${"test"})
          `;
          const visible = await transaction`
            select id from relay_hosts where id = ${hostId} for update
          `;
          assertEquals(visible[0].id, hostId);
          throw new Error("intentional rollback");
        });
      } catch (error) {
        assertEquals((error as Error).message, "intentional rollback");
        rolledBack = true;
      }
      assert(rolledBack, "transaction did not surface its failure");
      const persisted = await pool.query(
        "select id from relay_hosts where id = $1",
        [hostId],
      );
      assertEquals(persisted.rows.length, 0);
    } finally {
      await pool.query("delete from relay_hosts where id = $1", [hostId]);
      await pool.end();
    }
  },
});
