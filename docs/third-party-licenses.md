# Third-party dependency and license inventory

Inventory date: 2026-09-25. This is an engineering review, not legal advice.
Exact resolved versions are recorded in `requirements-windows-build.txt`,
`desktop/package-lock.json`, and `desktop/src-tauri/Cargo.lock`.

## Python runtime and build dependencies

| Dependency | Validated version | Role | License |
| --- | ---: | --- | --- |
| FastAPI | 0.141.1 | HTTP API/application | MIT |
| Uvicorn | 0.53.0 | loopback ASGI server | BSD-3-Clause |
| Jinja2 | 3.1.6 | dashboard templates | BSD-3-Clause |
| PyInstaller | 6.22.3 | Windows sidecar builder/bootloader | GPL-2.0-or-later with the PyInstaller exception allowing distribution of bundled applications |
| pytest | 9.1.1 | tests only | MIT |
| setuptools | 84.0.0 | Python build backend | MIT |

Resolved Python transitives are pinned in the Windows build requirements. Their
observed licenses are permissive (MIT, BSD, Apache-family, PSF-compatible, or
similarly permissive); re-run the inventory whenever the lock changes.

## Rust/Tauri distribution dependencies

| Direct dependency | Locked version | License expression |
| --- | ---: | --- |
| tauri | 2.11.6 | Apache-2.0 OR MIT |
| tauri-build | 2.6.3 | Apache-2.0 OR MIT |
| tauri-plugin-autostart | 2.5.1 | Apache-2.0 OR MIT |
| tauri-plugin-shell | 2.3.6 | Apache-2.0 OR MIT |
| tauri-plugin-single-instance | 2.4.5 | Apache-2.0 OR MIT |
| serde_json | 1.0.151 | MIT OR Apache-2.0 |
| url | 2.5.8 | MIT OR Apache-2.0 |

The resolved Cargo graph is predominantly MIT/Apache/BSD/Zlib/Unicode licensed.
Five resolved CSS/parser packages are MPL-2.0; two `r-efi` versions offer a
choice including MIT or Apache-2.0. No resolved Rust package declared GPL or
AGPL as its only license. MPL-2.0 is file-level copyleft and should be reviewed
again with the final GPLv3/AGPLv3 choice, but this audit found no obvious direct
license blocker.

## JavaScript and installer tooling

The dashboard bundles no third-party JavaScript library. It uses repository
HTML/CSS/vanilla JavaScript.

`@tauri-apps/cli` is locked to 2.11.5 and declares `Apache-2.0 OR MIT`; its
platform packages carry the same expression. Tauri downloads/uses NSIS to build
the Windows installer; NSIS uses the zlib/libpng license. Microsoft Edge
WebView2 is a separately installed Microsoft runtime, not project source.

Codex CLI is discovered from the user's machine and is **not bundled**.

## Compatibility finding

No direct dependency reviewed here presents an identified blocker to either
GPLv3 or AGPLv3 distribution. Final license counsel/review should confirm:

- PyInstaller exception and required notices for the shipped bootloader;
- MPL-2.0 notices/source obligations for relevant transitive files;
- complete third-party notices generated from the exact release lockfiles;
- WebView2 bootstrapper terms used by the installer.

Changing dependencies or lockfiles requires refreshing this inventory before a
public release candidate is approved.
