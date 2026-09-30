from pathlib import Path
import re
import tomllib

from app.version import (
    __version__,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

RELAY_REQUIREMENTS = PROJECT_ROOT / "requirements-relay-dev.txt"

PYPROJECT = (
    PROJECT_ROOT
    / "pyproject.toml"
)


def load_pyproject():
    with PYPROJECT.open(
        "rb"
    ) as handle:
        return tomllib.load(
            handle
        )


def test_project_metadata():
    data = load_pyproject()

    assert (
        data["project"]["name"]
        == "flightmargin"
    )

    assert (
        data["project"]["dynamic"]
        == ["version"]
    )

    assert (
        data["tool"]["setuptools"]
        ["dynamic"]["version"]
        == {"attr": "app.version.__version__"}
    )

    assert (
        "version"
        not in data["project"]
    )


def test_canonical_version_is_valid():
    assert re.fullmatch(
        r"[0-9]+(?:\.[0-9]+)+(?:[a-zA-Z0-9.+-]+)?",
        __version__,
    )
    assert __version__ == "0.3.0-beta.1"


def test_console_script():
    data = load_pyproject()

    assert data["project"]["scripts"] == {
        "flightmargin": "app.cli:main",
        "codex-quota": "app.cli:main",
    }


def test_project_license():
    assert load_pyproject()["project"]["license"] == {
        "text": "AGPL-3.0-or-later",
    }


def test_runtime_dependencies():
    data = load_pyproject()

    dependencies = set(
        data["project"][
            "dependencies"
        ]
    )

    assert dependencies == {
        "fastapi",
        "uvicorn",
        "jinja2",
    }


def test_package_discovery_excludes_local_relay_reference():
    packages = load_pyproject()["tool"]["setuptools"]["packages"]["find"]

    assert packages["include"] == ["app", "app.*"]


def test_relay_development_requirements_are_isolated():
    assert RELAY_REQUIREMENTS.read_text(encoding="utf-8").splitlines() == [
        "-r requirements.txt",
        "-r requirements-dev.txt",
        "httpx2>=2,<3",
        "psycopg[binary]>=3.2,<4",
    ]


def test_package_data():
    data = load_pyproject()

    package_data = (
        data["tool"]
        ["setuptools"]
        ["package-data"]
        ["app"]
    )

    assert (
        "templates/*.html"
        in package_data
    )

    assert (
        "static/*"
        in package_data
    )


def test_mobile_relay_client_is_packaged_but_reference_server_is_not():
    packages = load_pyproject()["tool"]["setuptools"]["packages"]["find"]

    assert packages["include"] == ["app", "app.*"]
    assert (PROJECT_ROOT / "app" / "mobile_relay" / "client.py").is_file()
    assert (PROJECT_ROOT / "app" / "static" / "qrcode.min.js").is_file()
    verification = (PROJECT_ROOT / "scripts" / "verify-release.py").read_text(
        encoding="utf-8"
    )
    for path in (
        "app/mobile_relay/__init__.py",
        "app/mobile_relay/client.py",
        "app/mobile_relay/config.py",
        "app/mobile_relay/identity.py",
        "app/mobile_relay/sync.py",
        "app/static/qrcode.min.js",
        "app/static/qrcode.LICENSE.txt",
    ):
        assert f'"{path}"' in verification
