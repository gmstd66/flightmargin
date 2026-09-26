# Public beta versioning recommendation

Current canonical internal version: `0.2.0`

Recommended first public beta: `0.3.0-beta.1`

The 0.2.0 line records internal architecture and Windows owner-validation work.
It should remain an internal development line so the first public artifact has
a clear prerelease identity and does not imply that earlier internal installers
were supported public releases.

Recommended progression:

```text
0.3.0-beta.1
0.3.0-beta.2
0.3.0-beta.3
0.3.0
```

Recommended Git tag for the first beta:

```text
v0.3.0-beta.1
```

Each beta increment should represent a new reviewed installer. `0.3.0` should
follow only after beta blockers are resolved and signing/distribution behavior
is stable. The application, Python metadata, Tauri config, Cargo metadata,
installer, tag, and release title must agree.

Milestone 6.20A does not change `app.version`, create a tag, or create a release.
The owner must approve the version immediately before the release candidate is
built.
