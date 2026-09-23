# Codex Quota Monitor

A local-first browser dashboard for monitoring OpenAI Codex usage limits.

Current features:

- 5-hour quota monitoring
- Weekly quota monitoring
- 1-minute sampling
- SQLite history
- 7-day usage graph
- Sustainable usage pace calculation
- Projected quota exhaustion
- Available full-reset credit display
- Manual refresh
- FastAPI web interface

## Current deployment

The initial working deployment runs on Linux using:

- Python
- FastAPI
- Uvicorn
- SQLite
- `codex app-server --stdio`

The application reads structured Codex rate-limit data from:

`account/rateLimits/read`

## Development status

The current codebase represents the original working Linux/server prototype.

Future development will focus on:

- portable core architecture
- automated diagnostics
- Linux installer
- Docker deployment
- desktop application
- Windows/macOS/Linux support

## License

License to be selected before public release.
