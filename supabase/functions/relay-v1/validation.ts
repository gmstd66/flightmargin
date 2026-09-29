import type { HostRegistration, PairingClaim, QuotaReport } from "./types.ts";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

function objectValue(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("Expected an object");
  }
  return value as Record<string, unknown>;
}

function exactFields(
  value: Record<string, unknown>,
  required: string[],
  optional: string[] = [],
): void {
  const allowed = new Set([...required, ...optional]);
  if (
    required.some((field) => !(field in value)) ||
    Object.keys(value).some((field) => !allowed.has(field))
  ) {
    throw new Error("Unexpected or missing field");
  }
}

function boundedString(
  value: unknown,
  maximum: number,
  nullable = false,
): string | null {
  if (nullable && value === null) return null;
  if (typeof value !== "string" || value.length > maximum) {
    throw new Error("Invalid string");
  }
  return value;
}

function identityString(value: unknown, maximum: number): string {
  const parsed = boundedString(value, maximum);
  if (!parsed || !parsed.trim()) throw new Error("Invalid identity");
  return parsed;
}

function uuid(value: unknown): string {
  if (typeof value !== "string" || !UUID_PATTERN.test(value)) {
    throw new Error("Invalid UUID");
  }
  return value;
}

function timestamp(value: unknown, nullable = false): string | null {
  if (nullable && value === null) return null;
  if (
    typeof value !== "string" ||
    !/(?:Z|[+-]\d{2}:\d{2})$/.test(value) ||
    !Number.isFinite(Date.parse(value))
  ) {
    throw new Error("Invalid timestamp");
  }
  return new Date(value).toISOString();
}

function nullableNumber(
  value: unknown,
  minimum: number,
  maximum = Number.POSITIVE_INFINITY,
): number | null {
  if (value === null) return null;
  if (
    typeof value !== "number" || !Number.isFinite(value) || value < minimum ||
    value > maximum
  ) {
    throw new Error("Invalid number");
  }
  return value;
}

function nullableInteger(value: unknown, minimum: number): number | null {
  const parsed = nullableNumber(value, minimum);
  if (parsed !== null && !Number.isInteger(parsed)) throw new Error("Invalid integer");
  return parsed;
}

export function validateRegistration(value: unknown): HostRegistration {
  const body = objectValue(value);
  exactFields(body, ["host_id", "display_name", "platform", "credential"], [
    "app_version",
  ]);
  return {
    hostId: uuid(body.host_id),
    displayName: identityString(body.display_name, 120),
    platform: identityString(body.platform, 32),
    appVersion: body.app_version === undefined
      ? null
      : boundedString(body.app_version, 64, true),
    credential: boundedString(body.credential, 128)!,
  };
}

export function validateQuota(value: unknown): QuotaReport {
  const body = objectValue(value);
  const fields = [
    "schema_version",
    "sampled_at",
    "five_hour_used",
    "five_hour_reset_at",
    "weekly_used",
    "weekly_reset_at",
    "plan_type",
    "reset_credits_available",
    "credits_balance",
    "spend_control_reached",
    "rate_limit_reached_type",
    "collector_state",
    "collector_message_code",
  ];
  exactFields(body, ["schema_version", "sampled_at"], fields.slice(2));
  if (body.schema_version !== 1) throw new Error("Invalid schema version");
  const collectorState = body.collector_state ?? "ok";
  if (!new Set(["ok", "degraded", "error"]).has(String(collectorState))) {
    throw new Error("Invalid collector state");
  }
  const spendControl = body.spend_control_reached ?? null;
  if (spendControl !== null && typeof spendControl !== "boolean") {
    throw new Error("Invalid boolean");
  }
  return {
    schemaVersion: 1,
    sampledAt: timestamp(body.sampled_at)!,
    fiveHourUsed: nullableNumber(body.five_hour_used ?? null, 0, 100),
    fiveHourResetAt: timestamp(body.five_hour_reset_at ?? null, true),
    weeklyUsed: nullableNumber(body.weekly_used ?? null, 0, 100),
    weeklyResetAt: timestamp(body.weekly_reset_at ?? null, true),
    planType: boundedString(body.plan_type ?? null, 64, true),
    resetCreditsAvailable: nullableInteger(body.reset_credits_available ?? null, 0),
    creditsBalance: nullableNumber(body.credits_balance ?? null, 0),
    spendControlReached: spendControl,
    rateLimitReachedType: boundedString(body.rate_limit_reached_type ?? null, 64, true),
    collectorState: collectorState as QuotaReport["collectorState"],
    collectorMessageCode: boundedString(
      body.collector_message_code ?? null,
      128,
      true,
    ),
  };
}

export function validatePairingClaim(value: unknown): PairingClaim {
  const body = objectValue(value);
  exactFields(body, ["device_id", "display_name", "platform", "credential"], [
    "pairing_token",
    "manual_code",
  ]);
  const pairingToken = body.pairing_token === undefined
    ? null
    : boundedString(body.pairing_token, 128, true);
  const manualCode = body.manual_code === undefined
    ? null
    : boundedString(body.manual_code, 11, true);
  if ((pairingToken === null) === (manualCode === null)) {
    throw new Error("Exactly one pairing method is required");
  }
  return {
    pairingToken,
    manualCode,
    deviceId: uuid(body.device_id),
    displayName: identityString(body.display_name, 120),
    platform: identityString(body.platform, 32),
    credential: boundedString(body.credential, 128)!,
  };
}
