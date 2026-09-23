from pathlib import Path
import tomllib


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
        == "codex-quota-monitor"
    )

    assert (
        data["project"]["version"]
        == "0.2.0"
    )


def test_console_script():
    data = load_pyproject()

    assert (
        data["project"]["scripts"][
            "codex-quota"
        ]
        == "app.cli:main"
    )


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
