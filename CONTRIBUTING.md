# Contributing

Thank you for your interest in Codex Quota Monitor. The project is preparing
for a public beta but is not yet open for outside contributions because the
open-source license has not been selected.

After the repository and contribution process are opened:

1. Search existing issues before filing a duplicate.
2. Describe the operating system, application version, Codex CLI version,
   expected behavior, and observed behavior.
3. Use **Settings > About > Technical details > Copy diagnostics** for a
   sanitized environment summary. Never attach `auth.json`, tokens, quota
   payloads, account identity, or the SQLite database.
4. Keep changes focused and add tests for behavior changes.
5. Open changes against the development branch requested by the maintainers.

## Development checks

Run the Python suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

For desktop changes:

```powershell
Set-Location desktop
npm ci
npm run prepare
cargo check --locked --manifest-path src-tauri\Cargo.toml
cargo test --locked --manifest-path src-tauri\Cargo.toml
node --check ..\app\static\app.js
node --check ..\app\static\settings.js
```

Always run `git diff --check`. Do not commit `.venv`, `node_modules`, Cargo
`target`, installers, databases, logs, screenshots containing private data, or
Codex authentication files.

## Scope and conduct

Keep the approved Tauri, PyInstaller, FastAPI, loopback-only architecture unless
an issue explicitly discusses an architectural change. Be respectful and keep
technical discussion focused on reproducible behavior.

License terms for contributions will be documented when the owner selects the
project license. No contributor license agreement has been selected.
