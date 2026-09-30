const projectRef = process.env.SUPABASE_PROJECT_REF;
const databaseUrl = process.env.FLIGHTMARGIN_RELAY_DATABASE_URL;

if (!projectRef || !databaseUrl) {
  throw new Error(
    "SUPABASE_PROJECT_REF and FLIGHTMARGIN_RELAY_DATABASE_URL are required",
  );
}

let value;
try {
  value = new URL(databaseUrl);
} catch {
  throw new Error("FLIGHTMARGIN_RELAY_DATABASE_URL must be a valid URL");
}

const expectedUsername = `flightmargin_relay.${projectRef}`;
const validPoolerHost = /^[^.]+\.pooler\.supabase\.com$/i.test(value.hostname);

if (
  !["postgres:", "postgresql:"].includes(value.protocol) ||
  decodeURIComponent(value.username) !== expectedUsername ||
  value.password.length === 0 ||
  !validPoolerHost ||
  value.port !== "6543"
) {
  throw new Error(
    "FLIGHTMARGIN_RELAY_DATABASE_URL must use the dedicated relay role and " +
      "Supabase shared transaction pooler on port 6543",
  );
}
