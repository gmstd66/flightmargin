import os
from pathlib import Path
import shutil
import subprocess
import uuid

import psycopg
import pytest


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
RUNTIME_ROLE_MIGRATION = (
    PROJECT_ROOT
    / "supabase"
    / "migrations"
    / "20260930014000_relay_runtime_role.sql"
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


def test_runtime_role_migration_is_additive_and_password_free():
    sql = read_text(RUNTIME_ROLE_MIGRATION)
    statements = "\n".join(
        line for line in sql.splitlines() if not line.lstrip().startswith("--")
    )

    assert RUNTIME_ROLE_MIGRATION.name == "20260930014000_relay_runtime_role.sql"
    assert "create role flightmargin_relay" in sql
    assert "alter role flightmargin_relay with" in sql
    for attribute in (
        "login",
        "nosuperuser",
        "nocreatedb",
        "nocreaterole",
        "noreplication",
        "nobypassrls",
        "noinherit",
    ):
        assert attribute in sql
    assert "password" not in statements.lower()
    assert "grant usage on schema public to flightmargin_relay" in sql
    assert "grant create on schema public" not in sql
    assert "grant all" not in sql


def test_edge_function_disables_supabase_jwt_verification():
    config = read_text(PROJECT_ROOT / "supabase" / "config.toml")

    assert "[functions.relay-v1]" in config
    assert "verify_jwt = false" in config


def _workflow_job(workflow, name):
    marker = f"  {name}:\n"
    start = workflow.index(marker)
    next_job = workflow.find("\n  ", start + len(marker))
    while next_job != -1:
        candidate = workflow[next_job + 1 :].splitlines()[0]
        if candidate.endswith(":") and not candidate.startswith("    "):
            break
        next_job = workflow.find("\n  ", next_job + 1)
    return workflow[start:] if next_job == -1 else workflow[start:next_job]


def test_mobile_relay_deployment_workflow_is_manual_two_phase():
    workflow = read_text(
        PROJECT_ROOT / ".github" / "workflows" / "deploy-mobile-relay.yml"
    )
    prepare = _workflow_job(workflow, "prepare")
    deploy = _workflow_job(workflow, "deploy")

    assert "workflow_dispatch:" in workflow
    assert "push:" not in workflow
    assert "pull_request:" not in workflow
    trigger = workflow[workflow.index("on:\n") : workflow.index("\npermissions:")]
    assert trigger.count("workflow_dispatch:") == 1
    assert "required: true" in trigger
    assert "type: choice" in trigger
    choices = [
        line.strip()[2:]
        for line in trigger[trigger.index("        options:\n") :].splitlines()[1:]
        if line.strip().startswith("- ")
    ]
    assert choices == ["prepare", "deploy"]

    assert "if: ${{ inputs.phase == 'prepare' }}" in prepare
    assert "ref: ${{ github.sha }}" in prepare
    assert "supabase db push" in prepare
    assert "supabase functions deploy" not in prepare
    assert "FLIGHTMARGIN_RELAY_PEPPER: ${{ secrets." not in prepare
    assert "FLIGHTMARGIN_RELAY_DATABASE_URL: ${{ secrets." not in prepare
    assert "SUPABASE_DB_PASSWORD: ${{ secrets.SUPABASE_DB_PASSWORD }}" in prepare
    assert "selected commit ${GITHUB_SHA}" in prepare
    assert "phase=deploy on the SAME Git revision" in prepare

    assert "if: ${{ inputs.phase == 'deploy' }}" in deploy
    assert "ref: ${{ github.sha }}" in deploy
    assert "supabase db push" not in deploy
    assert "supabase functions deploy relay-v1" in deploy
    assert "SUPABASE_DB_PASSWORD" not in deploy
    assert (
        "FLIGHTMARGIN_RELAY_DATABASE_URL: "
        "${{ secrets.FLIGHTMARGIN_RELAY_DATABASE_URL }}"
    ) in deploy
    assert "FLIGHTMARGIN_RELAY_PEPPER: ${{ secrets.FLIGHTMARGIN_RELAY_PEPPER }}" in deploy
    assert "FLIGHTMARGIN_RELAY_DATABASE_URL=\"$FLIGHTMARGIN_RELAY_DATABASE_URL\"" in deploy
    assert "node scripts/validate-relay-database-url.mjs" in deploy
    assert "Deployed FlightMargin relay commit ${GITHUB_SHA}" in deploy
    assert "echo \"$FLIGHTMARGIN_RELAY_PEPPER\"" not in workflow
    assert "echo \"$FLIGHTMARGIN_RELAY_DATABASE_URL\"" not in workflow
    assert "echo \"${FLIGHTMARGIN_RELAY_PEPPER}" not in workflow
    assert "echo \"${FLIGHTMARGIN_RELAY_DATABASE_URL}" not in workflow


@pytest.mark.parametrize(
    ("url", "valid"),
    (
        (
            "postgresql://flightmargin_relay.abcdefghijklmnopqrst:secret@"
            "aws-0-us-east-1.pooler.supabase.com:6543/postgres",
            True,
        ),
        (
            "postgresql://postgres.abcdefghijklmnopqrst:secret@"
            "aws-0-us-east-1.pooler.supabase.com:6543/postgres",
            False,
        ),
        (
            "postgresql://flightmargin_relay.wrong:secret@"
            "aws-0-us-east-1.pooler.supabase.com:6543/postgres",
            False,
        ),
        (
            "postgresql://flightmargin_relay.abcdefghijklmnopqrst:secret@"
            "db.example.com:6543/postgres",
            False,
        ),
        (
            "postgresql://flightmargin_relay.abcdefghijklmnopqrst:secret@"
            "aws-0-us-east-1.pooler.supabase.com:5432/postgres",
            False,
        ),
        (
            "postgresql://flightmargin_relay.abcdefghijklmnopqrst@"
            "aws-0-us-east-1.pooler.supabase.com:6543/postgres",
            False,
        ),
    ),
)
def test_relay_database_url_workflow_validation(url, valid):
    if shutil.which("node") is None:
        pytest.skip("Node.js is unavailable")
    result = subprocess.run(
        ["node", "scripts/validate-relay-database-url.mjs"],
        cwd=PROJECT_ROOT,
        env={
            **os.environ,
            "SUPABASE_PROJECT_REF": "abcdefghijklmnopqrst",
            "FLIGHTMARGIN_RELAY_DATABASE_URL": url,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode == 0) is valid
    assert "secret" not in result.stdout
    assert "secret" not in result.stderr


def _relay_database_connection():
    database_url = os.environ.get("FLIGHTMARGIN_RELAY_DATABASE_URL")
    if not database_url:
        pytest.skip("local relay PostgreSQL configuration is unavailable")
    return psycopg.connect(database_url)


def test_runtime_role_attributes_privileges_and_policies():
    expected_privileges = {
        "relay_hosts": {"INSERT", "SELECT", "UPDATE"},
        "relay_host_credentials": {"INSERT", "SELECT", "UPDATE"},
        "relay_devices": {"INSERT", "SELECT", "UPDATE"},
        "relay_device_credentials": {"INSERT", "SELECT", "UPDATE"},
        "relay_pairing_sessions": {"INSERT", "SELECT", "UPDATE"},
        "relay_quota_state": {"INSERT", "SELECT", "UPDATE"},
        "relay_rate_limit_buckets": {"DELETE", "INSERT", "SELECT", "UPDATE"},
    }
    with _relay_database_connection() as connection:
        role = connection.execute(
            """
            select rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
                   rolreplication, rolbypassrls, rolinherit
            from pg_roles where rolname = 'flightmargin_relay'
            """
        ).fetchone()
        assert role == (True, False, False, False, False, False, False)

        grants = connection.execute(
            """
            select table_name, privilege_type
            from information_schema.role_table_grants
            where grantee = 'flightmargin_relay'
              and table_schema = 'public'
            """
        ).fetchall()
        actual_privileges = {table: set() for table in expected_privileges}
        for table, privilege in grants:
            assert table in expected_privileges, f"unexpected table grant: {table}"
            actual_privileges[table].add(privilege)
        assert actual_privileges == expected_privileges
        assert all(
            "DELETE" not in privileges
            for table, privileges in actual_privileges.items()
            if table != "relay_rate_limit_buckets"
        )
        assert connection.execute(
            "select has_schema_privilege('flightmargin_relay', 'public', 'USAGE')"
        ).fetchone() == (True,)
        assert connection.execute(
            "select has_schema_privilege('flightmargin_relay', 'public', 'CREATE')"
        ).fetchone() == (False,)

        policies = connection.execute(
            """
            select tablename, policyname, cmd, roles
            from pg_policies
            where schemaname = 'public'
              and 'flightmargin_relay' = any(roles)
            """
        ).fetchall()
        actual_policies = {
            (table, policy, command) for table, policy, command, _roles in policies
        }
        expected_policies = {
            (table, f"relay_runtime_{command.lower()}", command)
            for table, privileges in expected_privileges.items()
            for command in privileges
        }
        assert actual_policies == expected_policies


def test_runtime_role_rls_allows_relay_work_and_denies_extra_access():
    host_id = uuid.uuid4()
    host_credential_id = uuid.uuid4()
    device_id = uuid.uuid4()
    device_credential_id = uuid.uuid4()
    pairing_id = uuid.uuid4()
    digest_a = "a" * 64
    digest_b = "b" * 64
    digest_c = "c" * 64

    with _relay_database_connection() as connection:
        connection.execute("create table public.relay_unrelated_probe (id integer)")
        connection.execute("revoke all on public.relay_unrelated_probe from public")
        connection.execute("set role flightmargin_relay")
        connection.execute(
            "insert into relay_hosts (id, display_name, platform) values (%s, %s, %s)",
            (host_id, "Privilege test host", "test"),
        )
        connection.execute(
            """insert into relay_host_credentials (id, host_id, token_digest)
               values (%s, %s, %s)""",
            (host_credential_id, host_id, digest_a),
        )
        connection.execute(
            """insert into relay_devices (id, host_id, display_name, platform)
               values (%s, %s, %s, %s)""",
            (device_id, host_id, "Privilege test device", "test"),
        )
        connection.execute(
            """insert into relay_device_credentials (id, device_id, token_digest)
               values (%s, %s, %s)""",
            (device_credential_id, device_id, digest_b),
        )
        connection.execute(
            """insert into relay_pairing_sessions
               (id, host_id, qr_secret_digest, manual_code_digest, expires_at)
               values (%s, %s, %s, %s, now() + interval '5 minutes')""",
            (pairing_id, host_id, digest_a, digest_b),
        )
        connection.execute(
            """insert into relay_quota_state (host_id, sampled_at)
               values (%s, now())""",
            (host_id,),
        )
        connection.execute(
            """insert into relay_rate_limit_buckets
               (action, identity_digest, window_started_at, expires_at)
               values ('host-registration', %s, date_trunc('hour', now()),
                       date_trunc('hour', now()) + interval '1 hour')""",
            (digest_c,),
        )
        for table in (
            "relay_hosts",
            "relay_host_credentials",
            "relay_devices",
            "relay_device_credentials",
            "relay_pairing_sessions",
            "relay_quota_state",
            "relay_rate_limit_buckets",
        ):
            connection.execute(f"select 1 from {table} limit 1")
        connection.execute(
            "update relay_hosts set last_seen_at = now() where id = %s", (host_id,)
        )
        connection.execute(
            "delete from relay_rate_limit_buckets where identity_digest = %s",
            (digest_c,),
        )

        connection.execute("savepoint denied_delete")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute("delete from relay_hosts where id = %s", (host_id,))
        connection.execute("rollback to savepoint denied_delete")

        connection.execute("savepoint denied_unrelated")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute("select * from public.relay_unrelated_probe")
        connection.execute("rollback to savepoint denied_unrelated")
        connection.rollback()


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
