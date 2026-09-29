import { Pool, type PoolClient, type QueryResultRow } from "pg";
import {
  constantTimeEqual,
  credentialDigest,
  normalizeManualCode,
  pairingManualDigest,
  pairingQrDigest,
  parsePairingToken,
  randomSecret,
} from "./crypto.ts";
import {
  AuthenticationFailed,
  type HostRegistration,
  type PairingClaim,
  PairingFailed,
  type PairingMethod,
  type PairingResult,
  PairingUnavailable,
  type ParsedCredential,
  type QuotaReport,
  type RateLimitResult,
  RegistrationConflict,
  type RelayRepository,
} from "./types.ts";

const MANUAL_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
const encoder = new TextEncoder();

type Row = QueryResultRow & Record<string, unknown>;
type Queryable = Pick<Pool | PoolClient, "query">;
export interface Sql {
  (strings: TemplateStringsArray, ...values: unknown[]): Promise<Row[]>;
  begin<T>(operation: (transaction: Sql) => Promise<T>): Promise<T>;
}

// One lazily-created module-scope pool is shared by every invocation in a warm
// isolate. Its single client serializes concurrent work without query pipelining.
let sharedPool: Pool | undefined;
let sharedClient: Sql | undefined;
let sharedClientUrl: string | undefined;

function databaseUrl(): { url: string; hosted: boolean } {
  const value = Deno.env.get("FLIGHTMARGIN_RELAY_DATABASE_URL");
  if (!value) {
    throw new Error("FLIGHTMARGIN_RELAY_DATABASE_URL is required");
  }
  const parsed = new URL(value);
  const hosted = !["localhost", "127.0.0.1", "::1"].includes(parsed.hostname);
  if (
    hosted &&
    (parsed.port !== "6543" ||
      !parsed.hostname.endsWith(".pooler.supabase.com"))
  ) {
    throw new Error(
      "FLIGHTMARGIN_RELAY_DATABASE_URL must use the Supabase shared transaction pooler on port 6543",
    );
  }
  return { url: value, hosted };
}

function queryTag(queryable: Queryable): Sql {
  const sql = async (
    strings: TemplateStringsArray,
    ...values: unknown[]
  ): Promise<Row[]> => {
    let text = strings[0];
    for (let index = 0; index < values.length; index += 1) {
      text += `$${index + 1}${strings[index + 1]}`;
    }
    // Passing text and values separately uses the unnamed extended-query path;
    // no prepared/named statement can persist across pooler transactions.
    return (await queryable.query<Row>(text, values)).rows;
  };
  sql.begin = async <T>(operation: (transaction: Sql) => Promise<T>) => {
    if (!(queryable instanceof Pool)) {
      throw new Error("Nested transactions are not supported");
    }
    const connection = await (queryable as Pool).connect();
    try {
      await connection.query("BEGIN");
      const result = await operation(queryTag(connection));
      await connection.query("COMMIT");
      return result;
    } catch (error) {
      await connection.query("ROLLBACK");
      throw error;
    } finally {
      connection.release();
    }
  };
  return sql;
}

export function createPgClient(pool: Pool): Sql {
  return queryTag(pool);
}

export function getClient(): Sql {
  const configuration = databaseUrl();
  if (!sharedPool || sharedClientUrl !== configuration.url) {
    sharedPool = new Pool({
      connectionString: configuration.url,
      max: 1,
      connectionTimeoutMillis: 5_000,
      idleTimeoutMillis: 20_000,
      maxLifetimeSeconds: 300,
      ssl: configuration.hosted ? { rejectUnauthorized: true } : false,
    });
    sharedClient = createPgClient(sharedPool);
    sharedClientUrl = configuration.url;
  }
  return sharedClient!;
}

function iso(value: unknown): string {
  return value instanceof Date
    ? value.toISOString()
    : new Date(String(value)).toISOString();
}

function numberOrNull(value: unknown): number | null {
  return value === null || value === undefined ? null : Number(value);
}

function randomManualCode(): string {
  const random = crypto.getRandomValues(new Uint8Array(10));
  const code = Array.from(random, (byte) => MANUAL_ALPHABET[byte % 32]).join("");
  return `${code.slice(0, 5)}-${code.slice(5)}`;
}

export class PostgresRelayRepository implements RelayRepository {
  constructor(
    private readonly pepper: Uint8Array,
    private readonly sql: Sql = getClient(),
  ) {}

  async rateLimit(
    action: "host-registration" | "pairing-claim",
    identityDigest: string,
    windowSeconds: number,
    limit: number,
  ): Promise<RateLimitResult> {
    const rows = await this.sql.begin(async (transaction) => {
      await transaction`set local statement_timeout = '5s'`;
      await transaction`
        delete from relay_rate_limit_buckets where expires_at < now()
      `;
      return await transaction`
        insert into relay_rate_limit_buckets (
          action, identity_digest, window_started_at, expires_at, request_count
        ) values (
          ${action}, ${identityDigest},
          to_timestamp(floor(extract(epoch from now()) / ${windowSeconds}) * ${windowSeconds}),
          to_timestamp((floor(extract(epoch from now()) / ${windowSeconds}) + 1) * ${windowSeconds}),
          1
        )
        on conflict (action, identity_digest, window_started_at)
        do update set request_count = relay_rate_limit_buckets.request_count + 1
        returning request_count,
          greatest(1, ceil(extract(epoch from (expires_at - now()))))::integer
            as retry_after
      `;
    });
    return {
      allowed: Number(rows[0].request_count) <= limit,
      retryAfter: Number(rows[0].retry_after),
    };
  }

  async registerHost(
    registration: HostRegistration,
    credential: ParsedCredential,
  ): Promise<boolean> {
    const digest = await credentialDigest(credential, this.pepper);
    return await this.sql.begin(async (transaction) => {
      await transaction`set local statement_timeout = '5s'`;
      const locks = [
        `relay-host:${registration.hostId}`,
        `relay-host-credential:${credential.credentialId}`,
      ].sort();
      for (const lock of locks) {
        await transaction`select pg_advisory_xact_lock(hashtextextended(${lock}, 0))`;
      }
      const hosts = await transaction`
        select id from relay_hosts where id = ${registration.hostId}
      `;
      const credentials = await transaction`
        select id, host_id, token_digest from relay_host_credentials
        where id = ${credential.credentialId}
      `;
      if (hosts.length === 0 && credentials.length === 0) {
        await transaction`
          insert into relay_hosts (id, display_name, platform, app_version)
          values (${registration.hostId}, ${registration.displayName},
            ${registration.platform}, ${registration.appVersion})
        `;
        await transaction`
          insert into relay_host_credentials (id, host_id, token_digest)
          values (${credential.credentialId}, ${registration.hostId}, ${digest})
        `;
        return true;
      }
      if (
        hosts.length === 1 && credentials.length === 1 &&
        credentials[0].host_id === registration.hostId &&
        constantTimeEqual(credentials[0].token_digest, digest)
      ) return false;
      throw new RegistrationConflict();
    });
  }

  async putQuota(
    credential: ParsedCredential,
    report: QuotaReport,
  ): Promise<boolean> {
    const digest = await credentialDigest(credential, this.pepper);
    return await this.sql.begin(async (transaction) => {
      await transaction`set local statement_timeout = '5s'`;
      const identity = await this.authenticateHost(
        transaction,
        credential.credentialId,
        digest,
      );
      await transaction`update relay_hosts set last_seen_at = now() where id = ${identity.host_id}`;
      await transaction`update relay_host_credentials set last_used_at = now() where id = ${credential.credentialId}`;
      const rows = await transaction`
        insert into relay_quota_state (
          host_id, schema_version, sampled_at, five_hour_used,
          five_hour_reset_at, weekly_used, weekly_reset_at, plan_type,
          reset_credits_available, credits_balance, spend_control_reached,
          rate_limit_reached_type, collector_state, collector_message_code
        ) values (
          ${identity.host_id}, ${report.schemaVersion}, ${report.sampledAt},
          ${report.fiveHourUsed}, ${report.fiveHourResetAt}, ${report.weeklyUsed},
          ${report.weeklyResetAt}, ${report.planType}, ${report.resetCreditsAvailable},
          ${report.creditsBalance}, ${report.spendControlReached},
          ${report.rateLimitReachedType}, ${report.collectorState},
          ${report.collectorMessageCode}
        ) on conflict (host_id) do update set
          schema_version = excluded.schema_version,
          sampled_at = excluded.sampled_at, received_at = now(),
          five_hour_used = excluded.five_hour_used,
          five_hour_reset_at = excluded.five_hour_reset_at,
          weekly_used = excluded.weekly_used,
          weekly_reset_at = excluded.weekly_reset_at,
          plan_type = excluded.plan_type,
          reset_credits_available = excluded.reset_credits_available,
          credits_balance = excluded.credits_balance,
          spend_control_reached = excluded.spend_control_reached,
          rate_limit_reached_type = excluded.rate_limit_reached_type,
          collector_state = excluded.collector_state,
          collector_message_code = excluded.collector_message_code
        where excluded.sampled_at > relay_quota_state.sampled_at
        returning host_id
      `;
      return rows.length === 1;
    });
  }

  async createPairing(credential: ParsedCredential): Promise<PairingResult> {
    const digest = await credentialDigest(credential, this.pepper);
    for (let attempt = 0; attempt < 5; attempt += 1) {
      const sessionId = crypto.randomUUID();
      const secret = randomSecret();
      const pairingToken = `fmp1.${sessionId}.${secret}`;
      const manualCode = randomManualCode();
      const qrDigest = await pairingQrDigest(
        parsePairingToken(pairingToken),
        this.pepper,
      );
      const manualDigest = await pairingManualDigest(
        normalizeManualCode(manualCode),
        this.pepper,
      );
      const result = await this.sql.begin(async (transaction) => {
        await transaction`set local statement_timeout = '5s'`;
        const identity = await this.authenticateHost(
          transaction,
          credential.credentialId,
          digest,
        );
        await transaction`
          select pg_advisory_xact_lock(
            hashtextextended(${`relay-pairing-manual:${manualDigest}`}, 0)
          )
        `;
        const collision = await transaction`
          select 1 from relay_pairing_sessions where manual_code_digest = ${manualDigest}
        `;
        if (collision.length) return null;
        await transaction`
          update relay_host_credentials set last_used_at = now()
          where id = ${credential.credentialId}
        `;
        const rows = await transaction`
          insert into relay_pairing_sessions (
            id, host_id, qr_secret_digest, manual_code_digest,
            expires_at, max_attempts
          ) values (
            ${sessionId}, ${identity.host_id}, ${qrDigest}, ${manualDigest},
            now() + interval '5 minutes', 5
          ) returning expires_at
        `;
        return iso(rows[0].expires_at);
      });
      if (result) return { pairingToken, manualCode, expiresAt: result };
    }
    throw new PairingUnavailable();
  }

  async claimPairing(
    claim: PairingClaim,
    deviceCredential: ParsedCredential,
    method: PairingMethod,
  ): Promise<string> {
    const pairingDigest = method.token
      ? await pairingQrDigest(method.token, this.pepper)
      : await pairingManualDigest(method.manualCode, this.pepper);
    const deviceDigest = await credentialDigest(deviceCredential, this.pepper);
    const outcome = await this.sql.begin(async (transaction) => {
      await transaction`set local statement_timeout = '5s'`;
      const sessions = method.token
        ? await transaction`
          select p.*, h.revoked_at as host_revoked_at,
            p.expires_at > now() as unexpired
          from relay_pairing_sessions p join relay_hosts h on h.id = p.host_id
          where p.id = ${method.token.sessionId} for update of p, h
        `
        : await transaction`
          select p.*, h.revoked_at as host_revoked_at,
            p.expires_at > now() as unexpired
          from relay_pairing_sessions p join relay_hosts h on h.id = p.host_id
          where p.manual_code_digest = ${pairingDigest}
          order by p.created_at desc limit 1 for update of p, h
        `;
      if (!sessions.length) {
        constantTimeEqual("0".repeat(64), pairingDigest);
        return { kind: "failed" as const };
      }
      const session = sessions[0];
      const expected = method.token
        ? session.qr_secret_digest
        : session.manual_code_digest;
      const matches = constantTimeEqual(expected, pairingDigest);
      if (session.claimed_at !== null) {
        if (!matches || session.host_revoked_at !== null) {
          return { kind: "failed" as const };
        }
        const stored = await transaction`
          select c.token_digest from relay_devices d
          join relay_device_credentials c on c.device_id = d.id
          where d.id = ${claim.deviceId} and c.id = ${deviceCredential.credentialId}
            and d.host_id = ${session.host_id} and d.revoked_at is null
            and c.revoked_at is null
        `;
        if (
          !stored.length || !constantTimeEqual(stored[0].token_digest, deviceDigest)
        ) {
          return { kind: "failed" as const };
        }
        return { kind: "success" as const, hostId: session.host_id };
      }
      if (
        session.host_revoked_at !== null || !session.unexpired ||
        Number(session.attempts) >= Number(session.max_attempts)
      ) return { kind: "failed" as const };
      if (!matches) {
        await transaction`
          update relay_pairing_sessions
          set attempts = least(attempts + 1, max_attempts) where id = ${session.id}
        `;
        return { kind: "failed" as const };
      }
      const locks = [
        `relay-device:${claim.deviceId}`,
        `relay-device-credential:${deviceCredential.credentialId}`,
      ].sort();
      for (const lock of locks) {
        await transaction`select pg_advisory_xact_lock(hashtextextended(${lock}, 0))`;
      }
      const existingDevice =
        await transaction`select 1 from relay_devices where id = ${claim.deviceId}`;
      const existingCredential =
        await transaction`select 1 from relay_device_credentials where id = ${deviceCredential.credentialId}`;
      if (existingDevice.length || existingCredential.length) {
        return { kind: "failed" as const };
      }
      await transaction`
        insert into relay_devices (id, host_id, display_name, platform)
        values (${claim.deviceId}, ${session.host_id}, ${claim.displayName}, ${claim.platform})
      `;
      await transaction`
        insert into relay_device_credentials (id, device_id, token_digest)
        values (${deviceCredential.credentialId}, ${claim.deviceId}, ${deviceDigest})
      `;
      await transaction`
        update relay_pairing_sessions set claimed_at = now(),
          claimed_device_id = ${claim.deviceId} where id = ${session.id}
      `;
      return { kind: "success" as const, hostId: session.host_id };
    });
    if (outcome.kind === "failed") throw new PairingFailed();
    return outcome.hostId;
  }

  async getQuota(credential: ParsedCredential): Promise<Record<string, unknown>> {
    const digest = await credentialDigest(credential, this.pepper);
    return await this.sql.begin(async (transaction) => {
      await transaction`set local statement_timeout = '5s'`;
      const identity = await this.authenticateDevice(
        transaction,
        credential.credentialId,
        digest,
      );
      await transaction`update relay_devices set last_seen_at = now() where id = ${identity.device_id}`;
      await transaction`update relay_device_credentials set last_used_at = now() where id = ${credential.credentialId}`;
      const hosts = await transaction`
        select id, display_name, platform, app_version, last_seen_at
        from relay_hosts where id = ${identity.host_id} and revoked_at is null
      `;
      if (!hosts.length) throw new AuthenticationFailed();
      const quotas = await transaction`
        select schema_version, sampled_at, received_at, five_hour_used,
          five_hour_reset_at, weekly_used, weekly_reset_at, plan_type,
          reset_credits_available, credits_balance, spend_control_reached,
          rate_limit_reached_type, collector_state, collector_message_code
        from relay_quota_state where host_id = ${identity.host_id}
      `;
      const host = hosts[0];
      const quota = quotas[0];
      return {
        api_version: 1,
        host: {
          id: host.id,
          display_name: host.display_name,
          platform: host.platform,
          app_version: host.app_version,
          last_seen_at: iso(host.last_seen_at),
        },
        quota: quota
          ? {
            schema_version: Number(quota.schema_version),
            sampled_at: iso(quota.sampled_at),
            received_at: iso(quota.received_at),
            five_hour_used: numberOrNull(quota.five_hour_used),
            five_hour_reset_at: quota.five_hour_reset_at
              ? iso(quota.five_hour_reset_at)
              : null,
            weekly_used: numberOrNull(quota.weekly_used),
            weekly_reset_at: quota.weekly_reset_at ? iso(quota.weekly_reset_at) : null,
            plan_type: quota.plan_type,
            reset_credits_available: quota.reset_credits_available,
            credits_balance: numberOrNull(quota.credits_balance),
            spend_control_reached: quota.spend_control_reached,
            rate_limit_reached_type: quota.rate_limit_reached_type,
            collector_state: quota.collector_state,
            collector_message_code: quota.collector_message_code,
          }
          : null,
      };
    });
  }

  private async authenticateHost(sql: Sql, credentialId: string, digest: string) {
    const rows = await sql`
      select c.id as credential_id, c.host_id, c.token_digest
      from relay_host_credentials c join relay_hosts h on h.id = c.host_id
      where c.id = ${credentialId} and c.revoked_at is null and h.revoked_at is null
      for update of c, h
    `;
    if (!rows.length || !constantTimeEqual(rows[0].token_digest, digest)) {
      throw new AuthenticationFailed();
    }
    return rows[0];
  }

  private async authenticateDevice(sql: Sql, credentialId: string, digest: string) {
    const rows = await sql`
      select c.id as credential_id, c.device_id, d.host_id, c.token_digest
      from relay_device_credentials c join relay_devices d on d.id = c.device_id
      join relay_hosts h on h.id = d.host_id
      where c.id = ${credentialId} and c.revoked_at is null
        and d.revoked_at is null and h.revoked_at is null
      for update of c, d, h
    `;
    if (!rows.length || !constantTimeEqual(rows[0].token_digest, digest)) {
      throw new AuthenticationFailed();
    }
    return rows[0];
  }
}

export function pepperFromEnvironment(): Uint8Array {
  const value = Deno.env.get("FLIGHTMARGIN_RELAY_PEPPER");
  if (!value || encoder.encode(value).length < 32) {
    throw new Error("FLIGHTMARGIN_RELAY_PEPPER must be at least 32 bytes");
  }
  return encoder.encode(value);
}
