export const RELAY_TEST_UNAVAILABLE_REASON =
  "relay integration tests require an explicitly configured local database";

export interface RelayTestConfig {
  databaseUrl: string;
  pepper: string;
}

interface RelayTestEnvironment {
  FLIGHTMARGIN_RELAY_TEST_DATABASE_URL?: string;
  FLIGHTMARGIN_RELAY_TEST_PEPPER?: string;
  FLIGHTMARGIN_RELAY_DATABASE_URL?: string;
  FLIGHTMARGIN_RELAY_PEPPER?: string;
}

function isLoopbackDatabaseUrl(value: string): boolean {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    return false;
  }
  if (parsed.protocol !== "postgres:" && parsed.protocol !== "postgresql:") {
    return false;
  }
  const hostname = parsed.hostname.toLowerCase();
  if (hostname === "localhost" || hostname === "[::1]") return true;
  const octets = hostname.split(".");
  return octets.length === 4 && octets.every((octet, index) => {
    if (!/^\d{1,3}$/.test(octet)) return false;
    const number = Number(octet);
    return number <= 255 && (index !== 0 || number === 127);
  });
}

export function resolveRelayTestConfig(
  environment: RelayTestEnvironment,
): RelayTestConfig | undefined {
  const explicitUrl = environment.FLIGHTMARGIN_RELAY_TEST_DATABASE_URL;
  const explicitPepper = environment.FLIGHTMARGIN_RELAY_TEST_PEPPER;
  const hasExplicitConfiguration = explicitUrl !== undefined ||
    explicitPepper !== undefined;
  const databaseUrl = hasExplicitConfiguration
    ? explicitUrl
    : environment.FLIGHTMARGIN_RELAY_DATABASE_URL;
  const pepper = hasExplicitConfiguration
    ? explicitPepper
    : environment.FLIGHTMARGIN_RELAY_PEPPER;
  if (!databaseUrl || !isLoopbackDatabaseUrl(databaseUrl)) return undefined;
  if (!pepper) return undefined;
  return { databaseUrl, pepper };
}

export function relayTestConfigFromEnvironment(): RelayTestConfig | undefined {
  return resolveRelayTestConfig({
    FLIGHTMARGIN_RELAY_TEST_DATABASE_URL: Deno.env.get(
      "FLIGHTMARGIN_RELAY_TEST_DATABASE_URL",
    ),
    FLIGHTMARGIN_RELAY_TEST_PEPPER: Deno.env.get(
      "FLIGHTMARGIN_RELAY_TEST_PEPPER",
    ),
    FLIGHTMARGIN_RELAY_DATABASE_URL: Deno.env.get(
      "FLIGHTMARGIN_RELAY_DATABASE_URL",
    ),
    FLIGHTMARGIN_RELAY_PEPPER: Deno.env.get("FLIGHTMARGIN_RELAY_PEPPER"),
  });
}
