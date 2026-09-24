from pathlib import Path

from app.core.environment import (
    check_directory_writable,
    codex_candidate_paths,
    detect_platform,
    find_codex,
)


def test_detect_platform_has_expected_fields():
    result = detect_platform()

    assert result["system"]
    assert result["release"]
    assert result["machine"]
    assert result["python"]


def test_writable_directory(tmp_path):
    assert check_directory_writable(
        tmp_path
    ) is True


def test_writable_directory_creates_missing_path(
    tmp_path,
):
    target = tmp_path / "nested" / "data"

    assert not target.exists()

    assert check_directory_writable(
        target
    ) is True

    assert target.is_dir()


def test_windows_codex_candidate_uses_documented_install_path(
    tmp_path,
):
    assert codex_candidate_paths(
        system="Windows",
        environ={"LOCALAPPDATA": str(tmp_path / "local")},
    ) == [
        tmp_path
        / "local"
        / "Programs"
        / "OpenAI"
        / "Codex"
        / "bin"
        / "codex.exe"
    ]


def test_find_codex_prefers_explicit_path(
    tmp_path,
):
    executable = tmp_path / "codex.exe"
    executable.touch()

    assert find_codex(
        system="Windows",
        environ={"CODEX_BIN": str(executable)},
        which=lambda _name: None,
    ) == str(executable)


def test_find_codex_uses_windows_standalone_fallback(
    tmp_path,
):
    local_app_data = tmp_path / "local"
    executable = (
        local_app_data
        / "Programs"
        / "OpenAI"
        / "Codex"
        / "bin"
        / "codex.exe"
    )
    executable.parent.mkdir(parents=True)
    executable.touch()

    assert find_codex(
        system="Windows",
        environ={"LOCALAPPDATA": str(local_app_data)},
        which=lambda _name: None,
    ) == str(executable)
