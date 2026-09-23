from pathlib import Path

from app.core.environment import (
    check_directory_writable,
    detect_platform,
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
