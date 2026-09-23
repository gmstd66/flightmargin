import os
from pathlib import Path

from app.adapters.codex_stdio import (
    CodexAppServer,
)

from app.core.quota import (
    normalize_rate_limits,
)

from app.storage.sqlite_store import (
    SQLiteQuotaStore,
)


APP_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

DATA_DIR = Path(
    os.environ.get(
        "CODEX_QUOTA_DATA_DIR",
        str(APP_ROOT / "data"),
    )
)

DATABASE_PATH = Path(
    os.environ.get(
        "CODEX_QUOTA_DB",
        str(DATA_DIR / "quota.db"),
    )
)


def main():
    codex = CodexAppServer()

    store = SQLiteQuotaStore(
        DATABASE_PATH
    )

    store.initialize()

    try:
        codex.start()

        response = (
            codex.get_rate_limits()
        )

        normalized = (
            normalize_rate_limits(
                response
            )
        )

        sample = (
            store.insert_sample(
                normalized
            )
        )

        five = sample.get(
            "five_hour_used"
        )

        weekly = sample.get(
            "weekly_used"
        )

        five_remaining = (
            100 - five
            if five is not None
            else None
        )

        weekly_remaining = (
            100 - weekly
            if weekly is not None
            else None
        )

        print(
            f"5h: {five_remaining}% remaining | "
            f"weekly: {weekly_remaining}% remaining | "
            f"resets available: "
            f"{sample.get('reset_credits_available')}"
        )

    finally:
        codex.stop()


if __name__ == "__main__":
    main()
