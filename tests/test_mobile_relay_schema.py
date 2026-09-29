from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    PROJECT_ROOT
    / "supabase"
    / "migrations"
    / "20260929173100_mobile_relay.sql"
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
