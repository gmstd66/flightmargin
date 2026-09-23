import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8093
DEFAULT_SAMPLE_SECONDS = 60


@dataclass(frozen=True)
class AppConfig:
    app_root: Path
    data_dir: Path
    database_path: Path
    host: str
    port: int
    sample_seconds: int
    codex_bin: str | None


def _env_int(
    name,
    default,
    minimum=None,
    maximum=None,
):
    raw = os.environ.get(name)

    if raw is None or raw == "":
        value = default
    else:
        try:
            value = int(raw)
        except ValueError as exc:
            raise ValueError(
                f"{name} must be an integer"
            ) from exc

    if (
        minimum is not None
        and value < minimum
    ):
        raise ValueError(
            f"{name} must be >= {minimum}"
        )

    if (
        maximum is not None
        and value > maximum
    ):
        raise ValueError(
            f"{name} must be <= {maximum}"
        )

    return value


def load_config():
    app_root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    data_dir = Path(
        os.environ.get(
            "CODEX_QUOTA_DATA_DIR",
            str(app_root / "data"),
        )
    ).expanduser()

    database_path = Path(
        os.environ.get(
            "CODEX_QUOTA_DB",
            str(data_dir / "quota.db"),
        )
    ).expanduser()

    host = os.environ.get(
        "CODEX_QUOTA_HOST",
        DEFAULT_HOST,
    )

    port = _env_int(
        "CODEX_QUOTA_PORT",
        DEFAULT_PORT,
        minimum=1,
        maximum=65535,
    )

    sample_seconds = _env_int(
        "CODEX_QUOTA_SAMPLE_SECONDS",
        DEFAULT_SAMPLE_SECONDS,
        minimum=10,
    )

    codex_bin = (
        os.environ.get("CODEX_BIN")
        or None
    )

    return AppConfig(
        app_root=app_root,
        data_dir=data_dir,
        database_path=database_path,
        host=host,
        port=port,
        sample_seconds=sample_seconds,
        codex_bin=codex_bin,
    )
