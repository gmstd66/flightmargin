import os
import sys
from pathlib import Path

from app.adapters.codex_stdio import CodexAppServer
from app.core.environment import (
    check_directory_writable,
    detect_platform,
    find_codex,
    get_codex_version,
)
from app.core.quota import normalize_rate_limits


APP_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = Path(
    os.environ.get(
        "CODEX_QUOTA_DATA_DIR",
        str(APP_ROOT / "data"),
    )
)


def mark(ok):
    return "✓" if ok else "✗"


def main():
    failures = 0

    print("Codex Quota Monitor — Doctor")
    print()

    platform_info = detect_platform()

    print(
        f"{mark(True)} Platform: "
        f"{platform_info['system']} "
        f"{platform_info['release']} "
        f"({platform_info['machine']})"
    )

    print(
        f"{mark(True)} Python: "
        f"{platform_info['python']}"
    )

    codex_bin = find_codex()

    if codex_bin:
        print(
            f"{mark(True)} Codex CLI: "
            f"{codex_bin}"
        )
    else:
        print(
            f"{mark(False)} Codex CLI not found"
        )
        failures += 1

    version = (
        get_codex_version(codex_bin)
        if codex_bin
        else None
    )

    if version:
        print(
            f"{mark(True)} Codex version: "
            f"{version}"
        )
    else:
        print(
            f"{mark(False)} Unable to read Codex version"
        )
        failures += 1

    writable = check_directory_writable(
        DATA_DIR
    )

    print(
        f"{mark(writable)} Data directory writable: "
        f"{DATA_DIR}"
    )

    if not writable:
        failures += 1

    if codex_bin:
        client = CodexAppServer(
            executable=codex_bin
        )

        try:
            client.start()

            response = (
                client.get_rate_limits()
            )

            normalized = (
                normalize_rate_limits(
                    response
                )
            )

            print(
                f"{mark(True)} Codex app-server reachable"
            )

            print(
                f"{mark(True)} Rate-limit API working"
            )

            plan = (
                normalized.get("plan_type")
                or "unknown"
            )

            print(
                f"{mark(True)} Account plan detected: "
                f"{plan}"
            )

            five = normalized.get(
                "five_hour_used"
            )

            weekly = normalized.get(
                "weekly_used"
            )

            if five is not None:
                print(
                    f"{mark(True)} 5-hour quota detected"
                )
            else:
                print(
                    f"{mark(False)} 5-hour quota not detected"
                )
                failures += 1

            if weekly is not None:
                print(
                    f"{mark(True)} Weekly quota detected"
                )
            else:
                print(
                    f"{mark(False)} Weekly quota not detected"
                )
                failures += 1

        except Exception as exc:
            print(
                f"{mark(False)} Codex app-server test failed: "
                f"{exc}"
            )
            failures += 1

        finally:
            client.stop()

    print()

    if failures:
        print(
            f"Doctor found {failures} problem(s)."
        )
        return 1

    print("Ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
