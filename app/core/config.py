import os
import platform
from dataclasses import dataclass
from pathlib import Path


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8093
DEFAULT_SAMPLE_SECONDS = 60
DEFAULT_APP_DATA_NAME = (
    "codex-quota-monitor"
)
DESKTOP_ENVIRONMENT_FLAG = "CODEX_QUOTA_DESKTOP"


@dataclass(frozen=True)
class AppConfig:
    app_root: Path
    data_dir: Path
    database_path: Path
    host: str
    port: int
    sample_seconds: int
    codex_bin: str | None
    desktop_mode: bool


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


def default_user_data_dir():
    xdg_data_home = os.environ.get(
        "XDG_DATA_HOME"
    )

    if xdg_data_home:
        return (
            Path(xdg_data_home)
            .expanduser()
            / DEFAULT_APP_DATA_NAME
        )

    return (
        Path.home()
        / ".local"
        / "share"
        / DEFAULT_APP_DATA_NAME
    )


def default_desktop_data_dir(
    system=None,
    environ=None,
    home=None,
):
    """Return the conventional per-user data directory for desktop mode.

    This intentionally avoids a third-party platform-path dependency while the
    application supports only these three desktop targets. Callers may still
    override the result with ``CODEX_QUOTA_DATA_DIR``.
    """
    environ = os.environ if environ is None else environ
    system = (system or platform.system()).lower()
    home = Path(home) if home is not None else Path.home()

    if system == "windows":
        local_app_data = environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "Codex Quota Monitor"
        return home / "AppData" / "Local" / "Codex Quota Monitor"

    if system == "darwin":
        return (
            home
            / "Library"
            / "Application Support"
            / "Codex Quota Monitor"
        )

    return default_user_data_dir_from(
        environ=environ,
        home=home,
    )


def default_user_data_dir_from(
    environ,
    home,
):
    """Internal parameterized form used by desktop path selection tests."""
    xdg_data_home = environ.get("XDG_DATA_HOME")

    if xdg_data_home:
        return Path(xdg_data_home).expanduser() / DEFAULT_APP_DATA_NAME

    return home / ".local" / "share" / DEFAULT_APP_DATA_NAME


def default_desktop_log_dir(
    system=None,
    environ=None,
    home=None,
):
    """Return the desktop log directory beside the per-user SQLite data."""
    return default_desktop_data_dir(
        system=system,
        environ=environ,
        home=home,
    ) / "logs"


def default_data_dir(
    app_root,
):
    app_root = Path(
        app_root
    )

    if (
        app_root
        / "pyproject.toml"
    ).is_file():
        return (
            app_root
            / "data"
        )

    return default_user_data_dir()


def load_config():
    app_root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    desktop_mode = os.environ.get(
        DESKTOP_ENVIRONMENT_FLAG,
        "",
    ).lower() in {"1", "true", "yes"}

    default_directory = (
        default_desktop_data_dir()
        if desktop_mode
        else default_data_dir(app_root)
    )

    data_dir = Path(
        os.environ.get(
            "CODEX_QUOTA_DATA_DIR",
            str(default_directory),
        )
    ).expanduser()

    database_path = Path(
        os.environ.get(
            "CODEX_QUOTA_DB",
            str(
                data_dir
                / "quota.db"
            ),
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
        os.environ.get(
            "CODEX_BIN"
        )
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
        desktop_mode=desktop_mode,
    )
