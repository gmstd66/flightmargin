from pathlib import Path

import pytest

from app.core.config import (
    DEFAULT_APP_DATA_NAME,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_SAMPLE_SECONDS,
    default_data_dir,
    default_user_data_dir,
    load_config,
)


ENV_NAMES = (
    "CODEX_QUOTA_DATA_DIR",
    "CODEX_QUOTA_DB",
    "CODEX_QUOTA_HOST",
    "CODEX_QUOTA_PORT",
    "CODEX_QUOTA_SAMPLE_SECONDS",
    "CODEX_BIN",
    "XDG_DATA_HOME",
)


def clear_config_environment(
    monkeypatch,
):
    for name in ENV_NAMES:
        monkeypatch.delenv(
            name,
            raising=False,
        )


def test_default_config(
    monkeypatch,
):
    clear_config_environment(
        monkeypatch
    )

    config = load_config()

    assert (
        config.host
        == DEFAULT_HOST
    )

    assert (
        config.port
        == DEFAULT_PORT
    )

    assert (
        config.sample_seconds
        == DEFAULT_SAMPLE_SECONDS
    )

    assert (
        config.data_dir
        == config.app_root / "data"
    )

    assert (
        config.database_path
        == config.data_dir / "quota.db"
    )

    assert config.codex_bin is None


def test_environment_overrides(
    monkeypatch,
    tmp_path,
):
    clear_config_environment(
        monkeypatch
    )

    data_dir = (
        tmp_path / "data"
    )

    database_path = (
        tmp_path / "custom.db"
    )

    monkeypatch.setenv(
        "CODEX_QUOTA_DATA_DIR",
        str(data_dir),
    )

    monkeypatch.setenv(
        "CODEX_QUOTA_DB",
        str(database_path),
    )

    monkeypatch.setenv(
        "CODEX_QUOTA_HOST",
        "0.0.0.0",
    )

    monkeypatch.setenv(
        "CODEX_QUOTA_PORT",
        "9001",
    )

    monkeypatch.setenv(
        "CODEX_QUOTA_SAMPLE_SECONDS",
        "120",
    )

    monkeypatch.setenv(
        "CODEX_BIN",
        "/custom/codex",
    )

    config = load_config()

    assert (
        config.data_dir
        == data_dir
    )

    assert (
        config.database_path
        == database_path
    )

    assert (
        config.host
        == "0.0.0.0"
    )

    assert (
        config.port
        == 9001
    )

    assert (
        config.sample_seconds
        == 120
    )

    assert (
        config.codex_bin
        == "/custom/codex"
    )


def test_database_defaults_to_data_dir(
    monkeypatch,
    tmp_path,
):
    clear_config_environment(
        monkeypatch
    )

    data_dir = (
        tmp_path / "data"
    )

    monkeypatch.setenv(
        "CODEX_QUOTA_DATA_DIR",
        str(data_dir),
    )

    config = load_config()

    assert (
        config.database_path
        == data_dir / "quota.db"
    )


def test_source_checkout_uses_local_data(
    tmp_path,
):
    project_root = (
        tmp_path / "project"
    )

    project_root.mkdir()

    (
        project_root
        / "pyproject.toml"
    ).write_text(
        "[project]\n",
        encoding="utf-8",
    )

    assert (
        default_data_dir(
            project_root
        )
        == (
            project_root
            / "data"
        )
    )


def test_installed_package_uses_user_data(
    monkeypatch,
    tmp_path,
):
    clear_config_environment(
        monkeypatch
    )

    monkeypatch.setenv(
        "HOME",
        str(tmp_path),
    )

    fake_site_packages = (
        tmp_path
        / "site-packages"
    )

    assert (
        default_data_dir(
            fake_site_packages
        )
        == (
            Path.home()
            / ".local"
            / "share"
            / DEFAULT_APP_DATA_NAME
        )
    )


def test_xdg_data_home(
    monkeypatch,
    tmp_path,
):
    clear_config_environment(
        monkeypatch
    )

    xdg_home = (
        tmp_path / "xdg-data"
    )

    monkeypatch.setenv(
        "XDG_DATA_HOME",
        str(xdg_home),
    )

    assert (
        default_user_data_dir()
        == (
            xdg_home
            / DEFAULT_APP_DATA_NAME
        )
    )


def test_invalid_port(
    monkeypatch,
):
    clear_config_environment(
        monkeypatch
    )

    monkeypatch.setenv(
        "CODEX_QUOTA_PORT",
        "70000",
    )

    with pytest.raises(
        ValueError
    ):
        load_config()


def test_invalid_sample_interval(
    monkeypatch,
):
    clear_config_environment(
        monkeypatch
    )

    monkeypatch.setenv(
        "CODEX_QUOTA_SAMPLE_SECONDS",
        "5",
    )

    with pytest.raises(
        ValueError
    ):
        load_config()


def test_non_integer_port(
    monkeypatch,
):
    clear_config_environment(
        monkeypatch
    )

    monkeypatch.setenv(
        "CODEX_QUOTA_PORT",
        "abc",
    )

    with pytest.raises(
        ValueError
    ):
        load_config()
