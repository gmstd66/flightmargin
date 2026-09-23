#!/usr/bin/env bash

set -euo pipefail


SERVICE_NAME="codex-quota"
DEFAULT_SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
    pwd
)"

PROJECT_DIR="$(
    cd -- "${SCRIPT_DIR}/.."
    pwd
)"

HOST="127.0.0.1"
PORT="8093"
SAMPLE_SECONDS="60"

SERVICE_USER="$(id -un)"
SERVICE_GROUP="$(id -gn)"
SERVICE_HOME="${HOME}"

PYTHON_EXECUTABLE="${PROJECT_DIR}/venv/bin/python"
CODEX_EXECUTABLE="$(command -v codex || true)"

SERVICE_PATH="${DEFAULT_SERVICE_PATH}"

APPLY=0


usage() {
    cat <<EOF
Codex Quota Monitor Linux installer

Usage:
  scripts/install-linux.sh [options]

Options:
  --host ADDRESS
      Dashboard bind address.
      Default: ${HOST}

  --port PORT
      Dashboard TCP port.
      Default: ${PORT}

  --sample-seconds SECONDS
      Codex quota sampling interval.
      Minimum: 10
      Default: ${SAMPLE_SECONDS}

  --user USER
      Systemd service user.
      Default: ${SERVICE_USER}

  --group GROUP
      Systemd service group.
      Default: ${SERVICE_GROUP}

  --home PATH
      HOME used by the service.
      Default: ${SERVICE_HOME}

  --python PATH
      Python executable.
      Default: ${PYTHON_EXECUTABLE}

  --codex PATH
      Codex CLI executable.
      Default: detected from PATH

  --service-path PATH
      Destination systemd unit.
      Default: ${SERVICE_PATH}

  --apply
      Actually install/reinstall the service.

  --dry-run
      Validate and print the generated unit
      without changing the system.
      This is the default.

  -h, --help
      Show this help.

Examples:

  Dry run:
    scripts/install-linux.sh

  Local-only service:
    scripts/install-linux.sh --apply

  LAN-accessible service:
    scripts/install-linux.sh \\
      --host 192.168.1.50 \\
      --port 8093 \\
      --apply
EOF
}


fail() {
    echo "ERROR: $*" >&2
    exit 1
}


info() {
    echo "==> $*"
}


ok() {
    echo "✓ $*"
}


while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)
            [[ $# -ge 2 ]] || fail "--host requires a value"
            HOST="$2"
            shift 2
            ;;

        --port)
            [[ $# -ge 2 ]] || fail "--port requires a value"
            PORT="$2"
            shift 2
            ;;

        --sample-seconds)
            [[ $# -ge 2 ]] || fail "--sample-seconds requires a value"
            SAMPLE_SECONDS="$2"
            shift 2
            ;;

        --user)
            [[ $# -ge 2 ]] || fail "--user requires a value"
            SERVICE_USER="$2"
            shift 2
            ;;

        --group)
            [[ $# -ge 2 ]] || fail "--group requires a value"
            SERVICE_GROUP="$2"
            shift 2
            ;;

        --home)
            [[ $# -ge 2 ]] || fail "--home requires a value"
            SERVICE_HOME="$2"
            shift 2
            ;;

        --python)
            [[ $# -ge 2 ]] || fail "--python requires a value"
            PYTHON_EXECUTABLE="$2"
            shift 2
            ;;

        --codex)
            [[ $# -ge 2 ]] || fail "--codex requires a value"
            CODEX_EXECUTABLE="$2"
            shift 2
            ;;

        --service-path)
            [[ $# -ge 2 ]] || fail "--service-path requires a value"
            SERVICE_PATH="$2"
            shift 2
            ;;

        --apply)
            APPLY=1
            shift
            ;;

        --dry-run)
            APPLY=0
            shift
            ;;

        -h|--help)
            usage
            exit 0
            ;;

        *)
            fail "Unknown option: $1"
            ;;
    esac
done


if [[ "$(uname -s)" != "Linux" ]]; then
    fail "This installer currently supports Linux only."
fi


[[ -d "${PROJECT_DIR}/app" ]] \
    || fail "Application directory not found: ${PROJECT_DIR}/app"

[[ -f "${PROJECT_DIR}/app/cli.py" ]] \
    || fail "CLI not found: ${PROJECT_DIR}/app/cli.py"

[[ -x "${PYTHON_EXECUTABLE}" ]] \
    || fail "Python executable not found: ${PYTHON_EXECUTABLE}"

[[ -n "${CODEX_EXECUTABLE}" ]] \
    || fail "Codex CLI was not found."

[[ -x "${CODEX_EXECUTABLE}" ]] \
    || fail "Codex executable is not executable: ${CODEX_EXECUTABLE}"


if ! [[ "${PORT}" =~ ^[0-9]+$ ]]; then
    fail "Port must be an integer."
fi

if (( PORT < 1 || PORT > 65535 )); then
    fail "Port must be between 1 and 65535."
fi


if ! [[ "${SAMPLE_SECONDS}" =~ ^[0-9]+$ ]]; then
    fail "Sample interval must be an integer."
fi

if (( SAMPLE_SECONDS < 10 )); then
    fail "Sample interval must be at least 10 seconds."
fi


command -v systemd-analyze >/dev/null 2>&1 \
    || fail "systemd-analyze was not found."

if (( APPLY == 1 )); then
    command -v systemctl >/dev/null 2>&1 \
        || fail "systemctl was not found."

    command -v sudo >/dev/null 2>&1 \
        || fail "sudo was not found."
fi


cd "${PROJECT_DIR}"


info "Running environment diagnostics"

CODEX_BIN="${CODEX_EXECUTABLE}" \
"${PYTHON_EXECUTABLE}" \
    -m app.doctor

ok "Environment diagnostics passed"


UNIT_FILE="$(
    mktemp \
        "/tmp/${SERVICE_NAME}.XXXXXX.service"
)"

cleanup() {
    rm -f "${UNIT_FILE}"
}

trap cleanup EXIT


info "Generating systemd unit"

CODEX_QUOTA_HOST="${HOST}" \
CODEX_QUOTA_PORT="${PORT}" \
CODEX_QUOTA_SAMPLE_SECONDS="${SAMPLE_SECONDS}" \
CODEX_BIN="${CODEX_EXECUTABLE}" \
"${PYTHON_EXECUTABLE}" \
    -m app.cli service-unit \
    --user "${SERVICE_USER}" \
    --group "${SERVICE_GROUP}" \
    --home "${SERVICE_HOME}" \
    --python-executable "${PYTHON_EXECUTABLE}" \
    --codex-executable "${CODEX_EXECUTABLE}" \
    > "${UNIT_FILE}"


info "Validating systemd unit"

systemd-analyze verify \
    "${UNIT_FILE}"

ok "Generated systemd unit is valid"


if (( APPLY == 0 )); then
    echo
    echo "=== GENERATED UNIT ==="
    cat "${UNIT_FILE}"

    echo
    echo "=== DRY RUN ==="
    echo "No system changes were made."
    echo
    echo "Would install:"
    echo "  ${UNIT_FILE}"
    echo "as:"
    echo "  ${SERVICE_PATH}"
    echo
    echo "Configuration:"
    echo "  Project:  ${PROJECT_DIR}"
    echo "  User:     ${SERVICE_USER}"
    echo "  Group:    ${SERVICE_GROUP}"
    echo "  HOME:     ${SERVICE_HOME}"
    echo "  Python:   ${PYTHON_EXECUTABLE}"
    echo "  Codex:    ${CODEX_EXECUTABLE}"
    echo "  Host:     ${HOST}"
    echo "  Port:     ${PORT}"
    echo "  Sample:   ${SAMPLE_SECONDS}s"

    exit 0
fi


TIMESTAMP="$(
    date '+%Y%m%d-%H%M%S'
)"

if sudo test -f "${SERVICE_PATH}"; then
    BACKUP_PATH="${SERVICE_PATH}.backup.${TIMESTAMP}"

    info "Backing up existing service"

    sudo cp \
        "${SERVICE_PATH}" \
        "${BACKUP_PATH}"

    ok "Backup created: ${BACKUP_PATH}"
fi


info "Installing systemd unit"

sudo install \
    -m 0644 \
    "${UNIT_FILE}" \
    "${SERVICE_PATH}"

ok "Installed ${SERVICE_PATH}"


info "Reloading systemd"

sudo systemctl daemon-reload


info "Enabling and starting service"

sudo systemctl enable \
    --now \
    "${SERVICE_NAME}"


info "Restarting service with generated configuration"

sudo systemctl restart \
    "${SERVICE_NAME}"


HEALTH_HOST="${HOST}"

if [[ "${HEALTH_HOST}" == "0.0.0.0" ]]; then
    HEALTH_HOST="127.0.0.1"
fi

if [[ "${HEALTH_HOST}" == "::" ]]; then
    HEALTH_HOST="127.0.0.1"
fi


HEALTH_URL="http://${HEALTH_HOST}:${PORT}/api/health"


info "Waiting for health endpoint"

HEALTH_OK=0

for _ in {1..15}; do
    if "${PYTHON_EXECUTABLE}" -c '
import json
import sys
import urllib.request

url = sys.argv[1]

try:
    with urllib.request.urlopen(
        url,
        timeout=2,
    ) as response:
        data = json.load(response)

    if data.get("status") == "ok":
        raise SystemExit(0)

except Exception:
    pass

raise SystemExit(1)
' "${HEALTH_URL}"
    then
        HEALTH_OK=1
        break
    fi

    sleep 1
done


if (( HEALTH_OK == 0 )); then
    echo
    echo "Service did not pass the health check."
    echo
    echo "Inspect with:"
    echo "  systemctl status ${SERVICE_NAME} --no-pager -l"
    echo
    echo "  journalctl -u ${SERVICE_NAME} -n 100 --no-pager"
    exit 1
fi


ok "Health endpoint responded successfully"


echo
echo "Codex Quota Monitor installed successfully."
echo
echo "Dashboard:"
echo "  http://${HEALTH_HOST}:${PORT}"
echo
echo "Service:"
echo "  ${SERVICE_NAME}"
echo
echo "Useful commands:"
echo "  systemctl status ${SERVICE_NAME}"
echo "  sudo systemctl restart ${SERVICE_NAME}"
echo "  journalctl -u ${SERVICE_NAME} -f"
