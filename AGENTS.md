# Codex Quota Monitor — Development Autonomy Policy

## Purpose

This repository uses bounded-autonomy development. Routine engineering work should proceed without requiring approval for every command or file edit. Human review is reserved for architectural decisions, production-impacting actions, destructive operations, and publication or release gates.

## Default working branch

Routine productization work should occur on a development or milestone branch rather than directly on `main`.

Default long-running branch:

`dev/productization`

Short-lived milestone branches may be used when useful, for example:

`dev/6.14-release`
`dev/6.15-docker`
`dev/6.16-desktop`

## Autonomous actions

The coding agent may perform these actions without additional approval when they remain inside the development environment:

- inspect repository files, history, tests, and documentation
- edit application code, tests, scripts, configuration, and documentation
- refactor internal code while preserving agreed behavior
- add or update tests
- run tests, linters, type checks, build commands, and local diagnostics
- build wheels and other non-published artifacts
- create temporary Python virtual environments
- create temporary SQLite databases
- run temporary application instances on unreserved development ports
- create temporary side-by-side test services using names beginning with `codex-quota-test-`
- inspect logs and diagnose failures
- iterate on failures until the approved milestone is green
- create commits on a development branch
- update implementation documentation

Do not stop for routine command approval.

## Protected production resources

The following are protected and must not be modified without explicit human approval:

- production checkout: `/opt/codex-quota`
- production systemd service: `codex-quota.service`
- production TCP port: `8093`
- production database: `/opt/codex-quota/data/quota.db`
- firewall or network exposure rules
- Codex authentication state or credentials
- secrets or credential stores
- production service user or permissions
- production data deletion or migration
- public package publication
- GitHub releases
- merges to `main`
- destructive Git history changes
- force pushes

Reading these resources for diagnostics is allowed when non-destructive.

## Development sandbox

Prefer development work under:

`<private-development-path>/`

Temporary test ports should normally use:

`18000-18999`

Never use port `8093` for a test instance.

Temporary systemd services should use names beginning with:

`codex-quota-test-`

Do not install test services from `/tmp` because the production hardening policy uses `PrivateTmp=true`, which can make executables under host `/tmp` unavailable to systemd services.

## Human decision gates

Stop and request approval before implementing any change that materially affects:

- application architecture or deployment model
- supported platforms
- security or authentication model
- production network exposure
- data model or destructive database migration
- externally visible compatibility guarantees
- dependency strategy when it adds substantial runtime or security surface
- licensing
- release/publication strategy
- merge to `main`
- production deployment

When a decision is needed, present the relevant options, tradeoffs, and a recommended technical direction. Do not ask for approval on routine implementation details.

## Milestone workflow

For an approved milestone, work through the full loop autonomously:

1. inspect current state
2. identify implementation constraints
3. implement the milestone
4. add or update tests
5. run the full relevant test suite
6. diagnose and fix failures
7. build and test artifacts when applicable
8. perform isolated side-by-side runtime validation when applicable
9. update documentation
10. commit the completed milestone on the development branch
11. report results and any remaining decision gates

A milestone should be returned to the human only when it is complete, blocked by a decision gate, or blocked by an external limitation.

## Completion report

At the end of each milestone, report:

- what changed
- tests and validation performed
- resulting commit SHA
- production impact: expected to be `none` unless separately approved
- any unresolved risks
- any architectural or production decision now requiring approval

## Safety principle

Prefer reversible, isolated, testable changes. Preserve user data and existing production behavior by default. When uncertain whether an action crosses a protected boundary, stop and ask rather than assume permission.
