import argparse
import signal
import time
from datetime import datetime

from app.codex_client import CodexClient
from app.database import initialize_database, insert_sample


RUNNING = True


def stop_handler(signum, frame):
    global RUNNING
    RUNNING = False


def identify_windows(limits):
    five_hour = None
    weekly = None

    for bucket in (
        limits.get("primary"),
        limits.get("secondary"),
    ):
        if not bucket:
            continue

        duration = bucket.get("windowDurationMins")

        if duration == 300:
            five_hour = bucket
        elif duration == 10080:
            weekly = bucket

    return five_hour, weekly


def normalize(raw):
    limits = raw["limits"]
    five_hour, weekly = identify_windows(limits)

    credits = limits.get("credits") or {}
    reset_credits = raw.get("reset_credits") or {}

    return {
        "five_hour_used":
            five_hour.get("usedPercent")
            if five_hour else None,

        "five_hour_reset_at":
            five_hour.get("resetsAt")
            if five_hour else None,

        "weekly_used":
            weekly.get("usedPercent")
            if weekly else None,

        "weekly_reset_at":
            weekly.get("resetsAt")
            if weekly else None,

        "plan_type":
            limits.get("planType"),

        "reset_credits_available":
            reset_credits.get("availableCount", 0),

        "credits_balance":
            credits.get("balance"),

        "spend_control_reached":
            limits.get("spendControlReached", False),

        "rate_limit_reached_type":
            limits.get("rateLimitReachedType"),
    }


def print_sample(sample):
    five_remaining = (
        100 - sample["five_hour_used"]
        if sample["five_hour_used"] is not None
        else None
    )

    weekly_remaining = (
        100 - sample["weekly_used"]
        if sample["weekly_used"] is not None
        else None
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(
        f"[{now}] "
        f"5h: {five_remaining}% remaining | "
        f"weekly: {weekly_remaining}% remaining | "
        f"resets available: "
        f"{sample['reset_credits_available']}",
        flush=True,
    )


def collect_once(client):
    raw = client.get_rate_limits()
    sample = normalize(raw)

    insert_sample(sample)
    print_sample(sample)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once",
        action="store_true",
        help="Collect one sample and exit",
    )
    args = parser.parse_args()

    initialize_database()

    client = CodexClient()

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    try:
        client.start()

        if args.once:
            collect_once(client)
            return

        while RUNNING:
            started = time.monotonic()

            try:
                collect_once(client)
            except Exception as exc:
                print(
                    f"Collection error: {exc}",
                    flush=True,
                )

                client.stop()

            elapsed = time.monotonic() - started
            sleep_for = max(0, 60 - elapsed)

            end = time.monotonic() + sleep_for

            while RUNNING and time.monotonic() < end:
                time.sleep(
                    min(1, end - time.monotonic())
                )

    finally:
        client.stop()


if __name__ == "__main__":
    main()
