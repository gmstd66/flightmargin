import sys
from pathlib import Path

from app.core.config import AppConfig
from app.core.environment import find_codex


DEFAULT_SYSTEM_PATH = (
    "/usr/local/bin:"
    "/usr/bin:"
    "/bin"
)


def _systemd_quote(value):
    value = str(value)

    value = value.replace(
        "\\",
        "\\\\",
    )

    value = value.replace(
        '"',
        '\\"',
    )

    return f'"{value}"'


def build_service_path(
    executable,
):
    executable_dir = str(
        Path(
            executable
        ).parent
    )

    return (
        f"{executable_dir}:"
        f"{DEFAULT_SYSTEM_PATH}"
    )


def render_systemd_unit(
    config: AppConfig,
    *,
    user,
    group=None,
    home=None,
    python_executable=None,
    cli_executable=None,
    codex_executable=None,
):
    group = group or user

    home = (
        Path(home).expanduser()
        if home
        else Path.home()
    )

    python_executable = (
        python_executable
        or sys.executable
    )

    codex_executable = (
        codex_executable
        or config.codex_bin
        or find_codex()
    )

    runtime_executable = (
        cli_executable
        or python_executable
    )

    service_path = build_service_path(
        runtime_executable
    )

    environment = [
        (
            "HOME",
            str(home),
        ),
        (
            "PATH",
            service_path,
        ),
        (
            "CODEX_QUOTA_DATA_DIR",
            str(config.data_dir),
        ),
        (
            "CODEX_QUOTA_DB",
            str(config.database_path),
        ),
        (
            "CODEX_QUOTA_HOST",
            config.host,
        ),
        (
            "CODEX_QUOTA_PORT",
            str(config.port),
        ),
        (
            "CODEX_QUOTA_SAMPLE_SECONDS",
            str(config.sample_seconds),
        ),
    ]

    if codex_executable:
        environment.append(
            (
                "CODEX_BIN",
                str(codex_executable),
            )
        )

    lines = [
        "[Unit]",
        "Description=Codex Quota Monitor",
        "After=network-online.target",
        "Wants=network-online.target",
        "",
        "[Service]",
        "Type=simple",
        f"User={user}",
        f"Group={group}",
        (
            "WorkingDirectory="
            f"{config.app_root}"
        ),
    ]

    for name, value in environment:
        lines.append(
            "Environment="
            + _systemd_quote(
                f"{name}={value}"
            )
        )

    if cli_executable:
        exec_start = (
            "ExecStart="
            + _systemd_quote(
                cli_executable
            )
            + " serve"
        )
    else:
        exec_start = (
            "ExecStart="
            + _systemd_quote(
                python_executable
            )
            + " -m app.cli serve"
        )

    lines.extend(
        [
            exec_start,
            "Restart=on-failure",
            "RestartSec=5",
            "NoNewPrivileges=true",
            "PrivateTmp=true",
            "",
            "[Install]",
            "WantedBy=multi-user.target",
            "",
        ]
    )

    return "\n".join(lines)
