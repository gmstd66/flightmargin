from pathlib import Path

from app import main


def test_package_root_is_app_directory():
    assert (
        main.PACKAGE_ROOT.name
        == "app"
    )


def test_templates_directory_exists():
    assert (
        main.TEMPLATES_DIR
        == (
            main.PACKAGE_ROOT
            / "templates"
        )
    )

    assert (
        main.TEMPLATES_DIR
        .is_dir()
    )


def test_dashboard_template_exists():
    template = (
        main.TEMPLATES_DIR
        / "index.html"
    )

    assert template.is_file()


def test_static_directory_exists():
    assert (
        main.STATIC_DIR
        == (
            main.PACKAGE_ROOT
            / "static"
        )
    )

    assert (
        main.STATIC_DIR
        .is_dir()
    )


def test_resource_paths_do_not_depend_on_repo_root():
    app_file = Path(
        main.__file__
    ).resolve()

    assert (
        main.PACKAGE_ROOT
        == app_file.parent
    )
