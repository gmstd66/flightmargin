from pathlib import Path

from app.core.config import (
    AppConfig,
)

from app.systemd import (
    build_service_path,
    render_systemd_unit,
)


def make_config():
    return AppConfig(
        app_root=Path(
            "/opt/codex-quota"
        ),
        data_dir=Path(
            "/var/lib/codex-quota"
        ),
        database_path=Path(
            "/var/lib/codex-quota/quota.db"
        ),
        host="10.0.0.25",
        port=8093,
        sample_seconds=60,
        codex_bin=None,
        desktop_mode=False,
    )


def test_service_identity():
    unit = render_systemd_unit(
        make_config(),
        user="quotauser",
        group="quotagroup",
        home="/home/quotauser",
        python_executable=(
            "/opt/codex-quota/"
            "venv/bin/python"
        ),
        codex_executable=(
            "/usr/bin/codex"
        ),
    )

    assert (
        "User=quotauser"
        in unit
    )

    assert (
        "Group=quotagroup"
        in unit
    )


def test_service_working_directory():
    unit = render_systemd_unit(
        make_config(),
        user="quotauser",
        python_executable=(
            "/venv/bin/python"
        ),
        codex_executable=(
            "/usr/bin/codex"
        ),
    )

    assert (
        "WorkingDirectory="
        "/opt/codex-quota"
        in unit
    )


def test_service_configuration():
    unit = render_systemd_unit(
        make_config(),
        user="quotauser",
        python_executable=(
            "/venv/bin/python"
        ),
        codex_executable=(
            "/usr/bin/codex"
        ),
    )

    assert (
        'Environment="'
        'CODEX_QUOTA_HOST='
        '10.0.0.25"'
        in unit
    )

    assert (
        'Environment="'
        'CODEX_QUOTA_PORT='
        '8093"'
        in unit
    )

    assert (
        'Environment="'
        'CODEX_QUOTA_SAMPLE_SECONDS='
        '60"'
        in unit
    )


def test_service_codex_executable():
    unit = render_systemd_unit(
        make_config(),
        user="quotauser",
        python_executable=(
            "/venv/bin/python"
        ),
        codex_executable=(
            "/usr/bin/codex"
        ),
    )

    assert (
        'Environment="'
        'CODEX_BIN=/usr/bin/codex"'
        in unit
    )


def test_legacy_service_exec_start():
    unit = render_systemd_unit(
        make_config(),
        user="quotauser",
        python_executable=(
            "/opt/codex-quota/"
            "venv/bin/python"
        ),
        codex_executable=(
            "/usr/bin/codex"
        ),
    )

    assert (
        'ExecStart="'
        '/opt/codex-quota/'
        'venv/bin/python" '
        '-m app.cli serve'
        in unit
    )


def test_cli_service_exec_start():
    unit = render_systemd_unit(
        make_config(),
        user="quotauser",
        python_executable=(
            "/opt/codex-quota/"
            "venv/bin/python"
        ),
        cli_executable=(
            "/opt/codex-quota/"
            "venv/bin/codex-quota"
        ),
        codex_executable=(
            "/usr/bin/codex"
        ),
    )

    assert (
        'ExecStart="'
        '/opt/codex-quota/'
        'venv/bin/codex-quota" '
        'serve'
        in unit
    )


def test_service_path_includes_venv():
    path = build_service_path(
        "/opt/codex-quota/"
        "venv/bin/python"
    )

    assert path.startswith(
        "/opt/codex-quota/"
        "venv/bin:"
    )

    assert (
        "/usr/local/bin:"
        "/usr/bin:"
        "/bin"
        in path
    )


def test_cli_service_path_includes_venv():
    unit = render_systemd_unit(
        make_config(),
        user="quotauser",
        cli_executable=(
            "/opt/codex-quota/"
            "venv/bin/codex-quota"
        ),
        codex_executable=(
            "/usr/bin/codex"
        ),
    )

    assert (
        'Environment="PATH='
        '/opt/codex-quota/'
        'venv/bin:'
        '/usr/local/bin:'
        '/usr/bin:'
        '/bin"'
        in unit
    )


def test_unit_contains_path():
    unit = render_systemd_unit(
        make_config(),
        user="quotauser",
        python_executable=(
            "/opt/codex-quota/"
            "venv/bin/python"
        ),
        codex_executable=(
            "/usr/bin/codex"
        ),
    )

    assert (
        'Environment="PATH='
        '/opt/codex-quota/'
        'venv/bin:'
        '/usr/local/bin:'
        '/usr/bin:'
        '/bin"'
        in unit
    )
