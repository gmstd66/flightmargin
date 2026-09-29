from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    PROJECT_ROOT
    / "supabase"
    / "migrations"
    / "20260929173100_mobile_relay.sql"
)
RATE_LIMIT_MIGRATION = (
    PROJECT_ROOT
    / "supabase"
    / "migrations"
    / "20260929203000_relay_rate_limits.sql"
)
DESIGN = (
    PROJECT_ROOT
    / "docs"
    / "mobile-relay-design.md"
)


def read_text(path):
    return path.read_text(encoding="utf-8")


def test_migration_uses_supabase_timestamp_filename():
    assert MIGRATION.name == "20260929173100_mobile_relay.sql"


def test_relay_schema_has_expected_tables():
    sql = read_text(MIGRATION)

    for table in (
        "relay_hosts",
        "relay_host_credentials",
        "relay_devices",
        "relay_device_credentials",
        "relay_pairing_sessions",
        "relay_quota_state",
    ):
        assert f"create table public.{table}" in sql


def test_relay_schema_blocks_direct_client_roles():
    sql = read_text(MIGRATION)

    for table in (
        "relay_hosts",
        "relay_host_credentials",
        "relay_devices",
        "relay_device_credentials",
        "relay_pairing_sessions",
        "relay_quota_state",
    ):
        assert (
            f"alter table public.{table} enable row level security;"
            in sql
        )
        assert (
            f"revoke all privileges on table public.{table}"
            in sql
        )


def test_relay_contract_keeps_supabase_credentials_server_side():
    design = read_text(DESIGN)

    assert "Clients do not receive a Supabase secret key" in design
    assert "iOS: Keychain." in design
    assert "HMAC-SHA-256" in design
    assert "no remote quota history in v1" in design.lower()


def test_rate_limit_migration_is_additive_and_protects_direct_access():
    sql = read_text(RATE_LIMIT_MIGRATION)

    assert RATE_LIMIT_MIGRATION.name == "20260929203000_relay_rate_limits.sql"
    assert "create table public.relay_rate_limit_buckets" in sql
    assert "primary key (action, identity_digest, window_started_at)" in sql
    assert "relay_rate_limit_buckets_expiry_idx" in sql
    assert "enable row level security" in sql
    assert "from anon, authenticated" in sql
    assert "raw" in sql.lower() and "never persisted" in sql.lower()


def test_edge_function_disables_supabase_jwt_verification():
    config = read_text(PROJECT_ROOT / "supabase" / "config.toml")

    assert "[functions.relay-v1]" in config
    assert "verify_jwt = false" in config


def test_mobile_relay_deployment_workflow_is_manual_only():
    workflow = read_text(
        PROJECT_ROOT / ".github" / "workflows" / "deploy-mobile-relay.yml"
    )

    assert "workflow_dispatch:" in workflow
    assert "push:" not in workflow
    assert "SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}" in workflow
    assert (
        "FLIGHTMARGIN_RELAY_DATABASE_URL: "
        "${{ secrets.FLIGHTMARGIN_RELAY_DATABASE_URL }}"
    ) in workflow
    assert "FLIGHTMARGIN_RELAY_PEPPER: ${{ secrets.FLIGHTMARGIN_RELAY_PEPPER }}" in workflow
    assert "FLIGHTMARGIN_RELAY_DATABASE_URL=\"$FLIGHTMARGIN_RELAY_DATABASE_URL\"" in workflow
    assert 'value.port !== "6543"' in workflow
    assert '.pooler.supabase.com' in workflow
    assert "echo \"$FLIGHTMARGIN_RELAY_PEPPER\"" not in workflow
    assert "echo \"$FLIGHTMARGIN_RELAY_DATABASE_URL\"" not in workflow
    assert workflow.count("SUPABASE_DB_PASSWORD: ${{ secrets.SUPABASE_DB_PASSWORD }}") == 2
    assert "supabase db push" in workflow
    assert "supabase functions deploy relay-v1" in workflow


def test_edge_function_uses_pooler_safe_node_postgres_configuration():
    function_root = PROJECT_ROOT / "supabase" / "functions" / "relay-v1"
    database = read_text(function_root / "db.ts")
    deno_config = read_text(function_root / "deno.json")

    assert 'Deno.env.get("FLIGHTMARGIN_RELAY_DATABASE_URL")' in database
    assert "SUPABASE_DB_URL" not in database
    assert 'from "pg"' in database
    assert '"pg": "npm:pg@' in deno_config
    assert "npm:postgres" not in deno_config
    assert "max: 1" in database
    assert "connectionTimeoutMillis: 5_000" in database
    assert 'connection.query("BEGIN")' in database
    assert 'connection.query("COMMIT")' in database
    assert 'connection.query("ROLLBACK")' in database
