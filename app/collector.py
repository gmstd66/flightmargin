from app.adapters.codex_stdio import (
    CodexAppServer,
)

from app.core.config import (
    load_config,
)

from app.core.quota import (
    normalize_rate_limits,
)

from app.storage.sqlite_store import (
    SQLiteQuotaStore,
)


def main():
    config = load_config()

    codex = CodexAppServer(
        executable=config.codex_bin
    )

    store = SQLiteQuotaStore(
        config.database_path
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
            f"5h: "
            f"{five_remaining}% remaining | "
            f"weekly: "
            f"{weekly_remaining}% remaining | "
            f"resets available: "
            f"{sample.get('reset_credits_available')}"
        )

    finally:
        codex.stop()


if __name__ == "__main__":
    main()
