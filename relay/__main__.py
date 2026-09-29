"""Run the local-only FlightMargin relay development server."""

import uvicorn


def main() -> None:
    uvicorn.run(
        "relay.main:app",
        host="127.0.0.1",
        port=18093,
        log_level="info",
    )


if __name__ == "__main__":
    main()
