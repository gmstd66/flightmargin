# Public beta versioning

Canonical application version: `0.3.0-beta.1`

Planned tag: `v0.3.0-beta.1`

`app/version.py` is the single source. The generated Cargo package and Tauri
application versions must match it exactly. Python wheel filenames and Core
Metadata use the standards-equivalent PEP 440 spelling `0.3.0b1`.

Expected progression:

```text
0.3.0-beta.1
0.3.0-beta.2
0.3.0-beta.3
0.3.0
```

The `0.2.0` line records internal work under the legacy Codex Quota Monitor
identity. No tag, package publication, GitHub Release, or public installer is
authorized by milestone 6.20D.1.
