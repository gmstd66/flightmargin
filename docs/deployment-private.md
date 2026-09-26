# Private deployment boundary

The project has an existing Linux/systemd deployment that predates the Windows
desktop beta. Its host name, LAN address, firewall rules, service account, and
operational paths are intentionally omitted from the public repository.

Production remains protected by `AGENTS.md`. Public project work must not
modify its checkout, service, reserved port, database, firewall, credentials,
authentication state, or permissions without separate owner approval.

Publicly useful Linux installation and lifecycle instructions are maintained in
[`installation-linux.md`](installation-linux.md). Those instructions use
generic example values and are separate from the private deployment record.
