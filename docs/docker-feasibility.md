# Docker Deployment Feasibility — Milestone 6.15

Status: investigation complete; no Docker deployment architecture has been selected or implemented.

This document records the development-host experiments performed on 2026-09-23. The experiments used only disposable images, containers, named volumes, temporary files, and loopback port `18098`. They did not modify the production checkout, service, database, port, firewall, or host authentication data.

## Executive result

A conventional container can install and execute the Codex CLI, and the least-privilege authentication layout can be separated from application data. However, the current Codex app-server cannot complete its sandbox setup inside this host's Docker default security profile. Therefore a self-contained, non-privileged Docker image is **not currently validated** for this application, because the app depends on `codex app-server --stdio` and `account/rateLimits/read`.

Do not add a production Dockerfile, Compose deployment, or image publication until a human selects one of the architecture options below.

## Container CLI findings

The following disposable image successfully installed and ran the pinned host CLI version:

```Dockerfile
FROM node:22-bookworm-slim
RUN apt-get update \
    && apt-get install --yes --no-install-recommends bubblewrap \
    && npm install --global @openai/codex@0.153.2
```

- Base: conventional Debian Bookworm Node 22 slim image.
- CLI install: `npm install --global @openai/codex@0.153.2`.
- Installed CLI: `codex-cli 0.153.2`.
- Package metadata requires Node `>=16`; Node 22 is the tested baseline.
- Host Docker platform: Linux/amd64. The package declares Linux x64 and Linux arm64 native payloads; an arm64 image still needs explicit validation.
- The CLI uses normal subprocess stdin/stdout in the container. The application adapter's JSON-RPC sequencing must be preserved: send `initialize`, await its response, then send `account/rateLimits/read`.

The application image would also need Python 3.10+ and the packaged wheel/runtime dependencies. The current app package itself is platform-neutral Python, but Codex supplies a native CLI payload for the target CPU architecture.

## Authentication and Codex home

Official OpenAI documentation states that file-backed Codex credentials are stored at `$CODEX_HOME/auth.json` (default `~/.codex/auth.json`) and should be treated as a password. It also documents copying only that file to a headless machine or container. See [Codex authentication](https://learn.chatgpt.com/docs/auth?translationFallback=zh-Hant).

The development host's `~/.codex` is not just credentials: it also contains session history, logs, caches, plugins, locks, and SQLite state. It must not be mounted wholesale into a container as a routine deployment practice.

### Model A: read-only host authentication mount

Tested variants:

- A read-only mount of the whole host `~/.codex` failed during `initialize` with:

  ```text
  failed to initialize sqlite state runtime under /home/app/.codex
  ```

  The host `auth.json` checksum was unchanged. The failure establishes that a completely read-only `CODEX_HOME` is insufficient.

- A read-only mount of **only** host `auth.json` over a separate writable Codex-state volume succeeded for `codex login status` and left the host credential checksum unchanged.

The minimal-file mount is materially safer than a whole-home mount, but it cannot be considered sufficient for quota reads until the app-server sandbox issue is resolved. In addition, OpenAI documents that ChatGPT tokens refresh during normal use, so a permanently read-only credential file may eventually prevent token refresh.

### Model B: copied/seeded authentication state

Tested layout:

```text
host auth.json (read-only during seed) → codex-auth named volume
app SQLite named volume                 → /data/quota.db
```

Seeding only `auth.json` into a disposable writable `CODEX_HOME` volume produced `Logged in using ChatGPT`. Codex then created only its own runtime files (for example `state_*.sqlite`, queue/log/state files, installation ID, and temporary directories) in that volume, separate from `/data/quota.db`.

New Docker volumes are root-owned. A non-root runtime user therefore needs a one-time volume ownership initialization step, or a host bind directory pre-owned by the configured container UID. The successful test ran Codex as the host UID/GID `1000:1000` after initialization.

This is the preferred credential-isolation pattern **if** direct in-container app-server execution becomes viable: do not bake auth into the image, do not commit it, and do not mount the broad host home. Decide explicitly whether the container may refresh its private copy or whether an operator reseeds it after expiry.

### Model C: independent container login

OpenAI documents `codex login --device-auth` as the preferred beta option for headless environments. It requires a user to open a browser, authenticate, and enter a one-time device code; credentials can then persist in a named Codex-home volume. Browser callback login is less practical in a headless container. See [Codex authentication](https://learn.chatgpt.com/docs/auth?translationFallback=zh-Hant#login-on-headless-devices).

This avoids copying host credentials but adds an interactive bootstrap/rotation workflow. It does not solve the app-server sandbox limitation. It is appropriate only if a human accepts the operational login experience.

### Other supported authentication

OpenAI documents `CODEX_ACCESS_TOKEN` for permitted ChatGPT Enterprise automation. It is an environment-controlled credential for trusted scripts and private CI runners, not a general replacement for a personal ChatGPT login. API keys are documented as the default for automation, but using either mechanism would change the application's authentication/entitlement model and requires a human decision. Neither was tested or added to this repository.

## App-server sandbox blocker

The application needs a persistent `codex app-server --stdio` subprocess. With the current Docker engine's default AppArmor/seccomp/cgroup namespace configuration, a non-root container failed the minimum bubblewrap namespace probe:

```text
bwrap: No permissions to create new namespace
```

Adding the Debian `bubblewrap` package did not make the app-server response available. Two narrower relaxation probes also failed:

- `--security-opt seccomp=unconfined`: `bwrap: Failed to make / slave: Permission denied`
- `--cap-add SYS_ADMIN`: the same mount-propagation failure

No privileged container was tested or used. A privileged container, Docker socket mount, broad host filesystem mount, or production Docker-daemon change is not an acceptable default for this project.

## Application data and network findings

- An isolated named volume mounted at `/data` retained `/data/quota.db` across separate containers. This confirms the desired persistent data boundary and is independent of the Codex-home/auth volume.
- A packaged dashboard container bound to `0.0.0.0:18098` internally and published explicitly as `127.0.0.1:18098:18098` returned HTTP 200 for `/api/health`, `/`, `/static/app.css`, and `/static/app.js`.
- The image needs no inbound service other than the dashboard port. Publish only an explicit host mapping; prefer loopback by default. Do not use production port `8093` for Docker testing.
- Codex requires outbound access for authentication and rate-limit requests. Do not change host firewall rules as part of this work.

## Security baseline for any future design

- No privileged container, Docker socket mount, host-root mount, production database mount, or credential in image/build context.
- Run the application and Codex under a non-root UID where practical; initialize writable volumes safely first.
- Keep the root filesystem read-only where compatible, with explicit writable volumes for `/data` and a private `CODEX_HOME`.
- Keep Codex credentials and application SQLite data in different volumes/directories.
- Bind the dashboard to `0.0.0.0` only inside the container and publish an explicit host address/port.

## Decision required before implementation

The following materially different paths remain:

| Option | Advantages | Costs and risks |
| --- | --- | --- |
| Keep the current systemd deployment | Known-working authenticated app-server; strongest current security posture | No Docker distribution |
| Containerize only the dashboard and use a host-side Codex app-server bridge | Keeps bubblewrap in the host environment where it works; container need not hold credentials | New host companion process/socket protocol and health model; changes deployment architecture |
| Make a self-contained container with a private seeded/login Codex volume | Portable image and clean auth/data separation | Current default Docker sandbox blocks app-server; solving it may require an unacceptable security relaxation or daemon change |
| Use an approved enterprise access token/API-key approach | Better automation and credential rotation story | Changes authentication and entitlement assumptions; requires Enterprise/API and explicit approval |

Recommended direction: retain the current systemd deployment until a human chooses either the host-side bridge design or an approved alternate authentication/sandbox model. Do not weaken Docker isolation merely to run bubblewrap.
