# Security policy

## Supported versions

There is no public supported release yet. Security fixes currently target the
public `main` and `dev/productization` source while the first Windows beta is
prepared.

## Reporting a vulnerability

Do not publish credentials, authentication files, exploit details, private
logs, databases, or account information in a public issue.

GitHub private vulnerability reporting is enabled. Use the repository's
**Security > Report a vulnerability** flow and include:

- affected version or commit;
- operating system;
- concise reproduction steps;
- security impact;
- whether credentials or user data may be affected.

The project does not currently offer a bug bounty or guaranteed response time.
Security-sensitive publication should be coordinated with the maintainer after
a fix and affected-release plan are ready.

## Security boundaries

The Windows desktop backend binds to an ephemeral loopback address. It reuses
the user's existing authenticated Codex CLI and must never copy, print, or
bundle its credentials. The Linux dashboard has no application-level
authentication and must not be exposed directly to the public internet.
