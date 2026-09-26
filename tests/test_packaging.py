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
    assert load_pyproject()["project"]["license"] == "AGPL-3.0-or-later"


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
