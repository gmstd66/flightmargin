# Third-party dependency and license inventory

Inventory date: 2026-09-30. This is an engineering review, not legal advice.
Exact resolved versions are recorded in `requirements-windows-build.txt`,
`desktop/package-lock.json`, and `desktop/src-tauri/Cargo.lock`.

For the Beta 1 candidate, all 27 pinned Python packages were compared with the
installed build environment and had no version mismatch. `cargo metadata
--locked --offline --format-version 1` resolved 498 Rust packages and found no
package without a declared license expression. The npm lock contains one
direct build tool, `@tauri-apps/cli`; its version and license matched this
inventory. These checks can be repeated from the repository without modifying
the lockfiles.

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
Five resolved CSS/parser packages are MPL-2.0: `cssparser 0.36.0`,
`cssparser-macros 0.6.1`, `dtoa-short 0.3.5`, `option-ext 0.2.0`, and
`selectors 0.36.1`. They are unmodified registry dependencies; the exact
upstream source is identified by `Cargo.lock`. Two `r-efi` versions offer an
MIT or Apache-2.0 choice in addition to LGPL. No resolved third-party Rust
package lacks a license declaration or declares GPL/AGPL as its only license;
FlightMargin itself is the expected AGPL-3.0-or-later package.

## JavaScript and installer tooling

The dashboard uses repository HTML/CSS/vanilla JavaScript. The Mobile Relay
pairing view vendors QRCode.js by davidshimjs (MIT, copyright 2012) solely to
render the relay-returned deep link without a CDN or runtime dependency. Its
license is packaged beside the source as `app/static/qrcode.LICENSE.txt`.

`@tauri-apps/cli` is locked to 2.11.5 and declares `Apache-2.0 OR MIT`; its
platform packages carry the same expression. Tauri downloads/uses NSIS to build
the Windows installer; NSIS uses the zlib/libpng license. Microsoft Edge
WebView2 is a separately installed Microsoft runtime, not project source.

Codex CLI is discovered from the user's machine and is **not bundled**.

## Compatibility finding

The PyInstaller exception expressly permits distribution of applications made
with its bootloader. The locked Python packages use MIT, BSD, Apache, PSF, or
the PyInstaller-exception terms recorded above. The MPL components are
unmodified, their exact versions and source locations remain traceable through
the public lockfile, and no vendored dependency source or local patch requires
a separate modified-source notice. The WebView2 Evergreen runtime is supplied
by Microsoft and is not bundled by FlightMargin; the installer may invoke
Microsoft's network bootstrapper if the runtime is absent. NSIS and the Tauri
CLI are build tools rather than application JavaScript dependencies.

No remaining third-party attribution blocker was identified by this engineering
review. QRCode.js is the one vendored runtime source and its full license ships
beside it; the public source, packaged notice, and exact lockfiles preserve the
reproducible dependency record. Changing dependencies, lockfiles, vendored
source, or WebView2 delivery mode requires refreshing this review.
