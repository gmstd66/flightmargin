import sqlite3
import time
from pathlib import Path


class SQLiteQuotaStore:

    def __init__(
        self,
        db_path,
    ):
        self.db_path = Path(
            db_path
        )


    def connect(self):
        conn = sqlite3.connect(
            self.db_path
        )

        conn.row_factory = (
            sqlite3.Row
        )

        return conn


    def initialize(self):
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quota_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    captured_at INTEGER NOT NULL,

                    five_hour_used REAL,
                    five_hour_reset_at INTEGER,

                    weekly_used REAL,
                    weekly_reset_at INTEGER,

                    plan_type TEXT,

                    reset_credits_available INTEGER,
                    credits_balance TEXT,

                    spend_control_reached INTEGER
                        NOT NULL DEFAULT 0,

                    rate_limit_reached_type TEXT
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_quota_samples_captured_at
                ON quota_samples(captured_at)
                """
            )


    def insert_sample(
        self,
        data,
    ):
        captured_at = int(
            time.time()
        )

        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO quota_samples (
                    captured_at,

                    five_hour_used,
                    five_hour_reset_at,

                    weekly_used,
                    weekly_reset_at,

                    plan_type,

                    reset_credits_available,
                    credits_balance,

                    spend_control_reached,
                    rate_limit_reached_type
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    captured_at,

                    data.get(
                        "five_hour_used"
                    ),

                    data.get(
                        "five_hour_reset_at"
                    ),

                    data.get(
                        "weekly_used"
                    ),

                    data.get(
                        "weekly_reset_at"
                    ),

                    data.get(
                        "plan_type"
                    ),

                    data.get(
                        "reset_credits_available"
                    ),

                    data.get(
                        "credits_balance"
                    ),

                    int(
                        data.get(
                            "spend_control_reached",
                            False,
                        )
                    ),

                    data.get(
                        "rate_limit_reached_type"
                    ),
                ),
            )

            sample_id = (
                cursor.lastrowid
            )

        return self.get_sample(
            sample_id
        )


    def get_sample(
        self,
        sample_id,
    ):
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM quota_samples
                WHERE id = ?
                """,
                (sample_id,),
            ).fetchone()

        return (
            dict(row)
            if row
            else None
        )


    def get_latest_sample(self):
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM quota_samples
                ORDER BY
                    captured_at DESC,
                    id DESC
                LIMIT 1
                """
            ).fetchone()

        return (
            dict(row)
            if row
            else None
        )


    def get_history(
        self,
        hours=168,
    ):
        since = (
            int(time.time())
            - hours * 3600
        )

        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM quota_samples
                WHERE captured_at >= ?
                ORDER BY
                    captured_at ASC,
                    id ASC
                """,
                (since,),
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]
