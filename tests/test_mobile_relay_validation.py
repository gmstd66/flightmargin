from __future__ import annotations

from datetime import UTC, datetime
from email.message import Message
import importlib.util
from pathlib import Path
import re
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "validate-mobile-relay.yml"
HOSTED_SCRIPT = PROJECT_ROOT / "scripts" / "validate-hosted-mobile-relay.py"
DPAPI_SCRIPT = PROJECT_ROOT / "scripts" / "validate-windows-dpapi.py"
SIDECAR_SMOKE = PROJECT_ROOT / "scripts" / "smoke-packaged-sidecar.py"
WINDOWS_TESTS = (
    "tests/test_about.py",
    "tests/test_cli.py",
    "tests/test_config.py",
    "tests/test_desktop.py",
    "tests/test_desktop_preferences.py",
    "tests/test_environment.py",
    "tests/test_identity.py",
    "tests/test_metrics.py",
    "tests/test_mobile_relay_host.py",
    "tests/test_mobile_relay_ui.py",
    "tests/test_mobile_relay_validation.py",
    "tests/test_packaging.py",
    "tests/test_platform_parity.py",
    "tests/test_quota_normalization.py",
    "tests/test_resources.py",
    "tests/test_windows_subprocess.py",
)


def load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


hosted = load_script(HOSTED_SCRIPT, "validate_hosted_mobile_relay")


class Response:
    def __init__(self, status, headers=None):
        self.status = status
        self.headers = headers or Message()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return b"{}"


def sequence_opener(statuses):
    remaining = iter(statuses)

    def open_request(_request, timeout):
        assert timeout == 15
        status = next(remaining)
        headers = Message()
        if status == 429:
            headers["Retry-After"] = "60"
        return Response(status, headers)

    return open_request


def test_hosted_validator_exercises_health_and_exact_public_thresholds(capsys):
    statuses = [200] + ([422] * 10) + [429] + ([422] * 20) + [429]

    hosted.validate_hosted_relay(opener=sequence_opener(statuses))

    assert capsys.readouterr().out.count("PASS") == 3


@pytest.mark.parametrize(
    ("statuses", "message"),
    [
        ([200, 429], "request 1"),
        ([200] + ([422] * 10) + [422], "threshold returned 422"),
    ],
)
def test_hosted_validator_rejects_wrong_threshold_behavior(statuses, message):
    with pytest.raises(RuntimeError, match=message):
        hosted.validate_hosted_relay(opener=sequence_opener(statuses))


class Cursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, sql):
        self.connection.selects.append(sql)

    def fetchall(self):
        return self.connection.snapshots.pop(0)

    def executemany(self, sql, parameters):
        self.connection.delete_sql = sql
        self.connection.deleted = list(parameters)


class Transaction:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class Connection:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.selects = []
        self.delete_sql = ""
        self.deleted = []

    def cursor(self):
        return Cursor(self)

    def transaction(self):
        return Transaction()


def test_rate_limit_cleanup_deletes_only_complete_new_primary_keys_on_error():
    started = datetime(2026, 9, 30, tzinfo=UTC)
    original = ("host-registration", "a" * 64, started)
    created = ("pairing-claim", "b" * 64, started)
    connection = Connection([[original], [original, created]])

    def fail():
        raise RuntimeError("validation failed")

    with pytest.raises(RuntimeError, match="validation failed"):
        hosted.validate_with_cleanup(connection, fail)

    assert len(connection.selects) == 2
    assert connection.deleted == [created]
    assert "action = %s" in connection.delete_sql
    assert "identity_digest = %s" in connection.delete_sql
    assert "window_started_at = %s" in connection.delete_sql
    assert "truncate" not in connection.delete_sql.lower()
    source = HOSTED_SCRIPT.read_text(encoding="utf-8").lower()
    assert "from public.relay_rate_limit_buckets" in source
    assert "truncate" not in source


def workflow_text():
    return WORKFLOW.read_text(encoding="utf-8")


def job_block(name: str, next_name: str | None = None) -> str:
    text = workflow_text()
    start = text.index(f"  {name}:\n")
    end = text.index(f"  {next_name}:\n", start) if next_name else len(text)
    return text[start:end]


def test_validation_workflow_is_manual_only_with_exact_choices():
    workflow = workflow_text()
    trigger = workflow[workflow.index("on:\n") : workflow.index("permissions:\n")]
    assert "workflow_dispatch:" in trigger
    assert "push:" not in trigger
    assert "pull_request:" not in trigger
    options = re.search(r"options:\n((?:          - .+\n)+)", trigger)
    assert options is not None
    assert re.findall(r"- (.+)", options.group(1)) == [
        "all",
        "hosted-rate-limits",
        "windows",
    ]


def test_hosted_job_has_only_required_database_secrets_and_exact_ref():
    hosted_job = job_block("hosted-rate-limits", "windows")
    assert "SUPABASE_PROJECT_REF: ${{ secrets.SUPABASE_PROJECT_REF }}" in hosted_job
    assert (
        "FLIGHTMARGIN_RELAY_DATABASE_URL: "
        "${{ secrets.FLIGHTMARGIN_RELAY_DATABASE_URL }}"
    ) in hosted_job
    assert set(re.findall(r"secrets\.([A-Z0-9_]+)", hosted_job)) == {
        "SUPABASE_PROJECT_REF",
        "FLIGHTMARGIN_RELAY_DATABASE_URL",
    }
    assert "SUPABASE_DB_PASSWORD" not in hosted_job
    assert "FLIGHTMARGIN_RELAY_PEPPER" not in hosted_job
    assert "node scripts/validate-relay-database-url.mjs" in hosted_job
    assert "validate-hosted-mobile-relay.py --confirm-hosted" in hosted_job
    assert "ref: ${{ github.sha }}" in hosted_job
    assert "persist-credentials: false" in hosted_job


def test_windows_job_has_no_supabase_secrets_or_hosted_contact():
    windows_job = job_block("windows")
    assert "secrets." not in windows_job
    assert "SUPABASE_DB_PASSWORD" not in windows_job
    assert "FLIGHTMARGIN_RELAY_DATABASE_URL" not in windows_job
    assert "samcdyrwfwrlxzypzgmj" not in windows_job
    assert "FLIGHTMARGIN_RELAY_ENDPOINT: http://127.0.0.1:9" in windows_job
    assert "validate-windows-dpapi.py" in windows_job
    assert "npm run tauri:build" in windows_job
    assert "scripts/verify-release.py" in windows_job
    assert "smoke-packaged-sidecar.py" in windows_job


def test_windows_job_uses_explicit_application_test_scope():
    windows_job = job_block("windows")
    test_step = windows_job[
        windows_job.index("      - name: Run Windows and mobile-host tests\n") :
        windows_job.index("      - name: Validate native Windows DPAPI\n")
    ]

    assert re.findall(r"tests/test_[a-z0-9_]+\.py", test_step) == list(WINDOWS_TESTS)
    assert not re.search(r"run: .* -m pytest -v\s*$", test_step, re.MULTILINE)
    for relay_server_test in (
        "tests/test_mobile_relay_api.py",
        "tests/test_mobile_relay_crypto_vectors.py",
        "tests/test_mobile_relay_schema.py",
        "tests/test_relay_test_config.py",
    ):
        assert relay_server_test not in test_step


def test_windows_job_preserves_application_dependencies_and_package_validation():
    windows_job = job_block("windows")

    assert "requirements-windows-build.txt" in windows_job
    assert "requirements-relay-dev.txt" not in windows_job
    assert "psycopg" not in windows_job.lower()
    assert "httpx2" not in windows_job.lower()
    assert "validate-windows-dpapi.py" in windows_job
    assert "npm run tauri:build" in windows_job
    assert "smoke-packaged-sidecar.py" in windows_job
    assert (
        "Get-ChildItem -LiteralPath desktop/src-tauri/target/release/bundle/nsis"
        in windows_job
    )


def test_workflow_has_no_deploy_migration_publish_or_release_commands():
    workflow = workflow_text().lower()
    forbidden = (
        "supabase db push",
        "supabase functions deploy",
        "supabase migration",
        "actions/upload-artifact",
        "gh release",
        "npm publish",
        "twine upload",
        "git push",
    )
    assert not [command for command in forbidden if command in workflow]
    assert "contents: read" in workflow


def test_native_validation_scripts_encode_required_safety_properties():
    dpapi = DPAPI_SCRIPT.read_text(encoding="utf-8")
    smoke = SIDECAR_SMOKE.read_text(encoding="utf-8")
    assert "HostIdentityStore(data_dir)" in dpapi
    assert "subprocess.run" in dpapi
    assert "corrupt_protected_credential" in dpapi
    assert "IdentityStorageError" in dpapi
    assert "TemporaryDirectory" in dpapi
    assert "FLIGHTMARGIN_RELAY_ENDPOINT" in smoke
    assert "http://127.0.0.1:9" in smoke
    assert 'environment.pop(secret_name, None)' in smoke
