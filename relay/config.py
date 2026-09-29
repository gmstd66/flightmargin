"""Relay configuration loaded from the two approved environment variables."""

from dataclasses import dataclass
import os


DATABASE_URL_ENV = "FLIGHTMARGIN_RELAY_DATABASE_URL"
PEPPER_ENV = "FLIGHTMARGIN_RELAY_PEPPER"


@dataclass(frozen=True)
class RelayConfig:
    database_url: str
    pepper: bytes

    def __post_init__(self) -> None:
        if len(self.pepper) < 32:
            raise ValueError(
                f"{PEPPER_ENV} must be at least 32 bytes"
            )

    @classmethod
    def from_environment(cls) -> "RelayConfig":
        database_url = os.environ.get(DATABASE_URL_ENV)
        pepper = os.environ.get(PEPPER_ENV)
        missing = [
            name
            for name, value in (
                (DATABASE_URL_ENV, database_url),
                (PEPPER_ENV, pepper),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Missing required relay configuration: " + ", ".join(missing)
            )
        return cls(database_url=database_url, pepper=pepper.encode("utf-8"))
