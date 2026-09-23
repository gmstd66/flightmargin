#!/usr/bin/env bash

set -euo pipefail


DEFAULT_SERVICE_NAME="codex-quota"
SERVICE_NAME="${DEFAULT_SERVICE_NAME}"
SERVICE_PATH_EXPLICIT=0

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

VENV_DIR="${PROJECT_DIR}/venv"
DEFAULT_RUNTIME_PYTHON="${VENV_DIR}/bin/python"

PYTHON_EXECUTABLE="${DEFAULT_RUNTIME_PYTHON}"
PYTHON_EXPLICIT=0

BOOTSTRAP_PYTHON="$(
    command -v python3 || true
)"

CODEX_EXECUTABLE="$(
    command -v codex || true
)"

SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

APPLY=0
INSTALL_DEV=0


usage() {
    cat <<EOF
Codex Quota Monitor Linux installer

Usage:
  scripts/install-linux.sh [options]

Options:
  --service-name NAME
      Systemd service name.

      Default:
        ${SERVICE_NAME}

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
      Existing Python executable to use
      for the installed application.

      If omitted, the installer uses:
        ${DEFAULT_RUNTIME_PYTHON}

      If that default virtual environment
      does not exist, --apply creates it.

  --bootstrap-python PATH
      Python used to create the virtual
      environment when needed.

      Default:
        ${BOOTSTRAP_PYTHON:-not detected}

  --venv PATH
      Virtual environment directory used
      when --python is not supplied.

      Default:
        ${VENV_DIR}

  --codex PATH
      Codex CLI executable.
      Default: detected from PATH

  --service-path PATH
      Destination systemd unit.

      Default:
        /etc/systemd/system/<service-name>.service

  --dev
      Install development dependencies
      from requirements-dev.txt instead
      of requirements.txt.

  --apply
      Create/install dependencies as needed
      and install/reinstall the service.

  --dry-run
      Validate the proposed installation
      without changing the system.
      This is the default.

  -h, --help
      Show this help.

Examples:

  Fresh-machine dry run:
    scripts/install-linux.sh

  Local-only service:
    scripts/install-linux.sh --apply

  LAN-accessible service:
    scripts/install-linux.sh \
      --host 192.168.1.50 \
      --port 8093 \
      --apply

  Side-by-side test service:
    scripts/install-linux.sh \
      --service-name codex-quota-test \
      --host 127.0.0.1 \
      --port 18097 \
      --apply

  Existing Python environment:
    scripts/install-linux.sh \
      --python /path/to/venv/bin/python \
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
        --service-name)
            [[ $# -ge 2 ]] \
                || fail "--service-name requires a value"

            SERVICE_NAME="$2"

            if (( SERVICE_PATH_EXPLICIT == 0 )); then
                SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
            fi

            shift 2
            ;;

        --host)
            [[ $# -ge 2 ]] \
                || fail "--host requires a value"

            HOST="$2"
            shift 2
            ;;

        --port)
            [[ $# -ge 2 ]] \
                || fail "--port requires a value"

            PORT="$2"
            shift 2
            ;;

        --sample-seconds)
            [[ $# -ge 2 ]] \
                || fail "--sample-seconds requires a value"

            SAMPLE_SECONDS="$2"
            shift 2
            ;;

        --user)
            [[ $# -ge 2 ]] \
                || fail "--user requires a value"

            SERVICE_USER="$2"
            shift 2
            ;;

        --group)
            [[ $# -ge 2 ]] \
                || fail "--group requires a value"

            SERVICE_GROUP="$2"
            shift 2
            ;;

        --home)
            [[ $# -ge 2 ]] \
                || fail "--home requires a value"

            SERVICE_HOME="$2"
            shift 2
            ;;

        --python)
            [[ $# -ge 2 ]] \
                || fail "--python requires a value"

            PYTHON_EXECUTABLE="$2"
            PYTHON_EXPLICIT=1
            shift 2
            ;;

        --bootstrap-python)
            [[ $# -ge 2 ]] \
                || fail "--bootstrap-python requires a value"

            BOOTSTRAP_PYTHON="$2"
            shift 2
            ;;

        --venv)
            [[ $# -ge 2 ]] \
                || fail "--venv requires a value"

            VENV_DIR="$2"

            if (( PYTHON_EXPLICIT == 0 )); then
                PYTHON_EXECUTABLE="${VENV_DIR}/bin/python"
            fi

            shift 2
            ;;

        --codex)
            [[ $# -ge 2 ]] \
                || fail "--codex requires a value"

            CODEX_EXECUTABLE="$2"
            shift 2
            ;;

        --service-path)
            [[ $# -ge 2 ]] \
                || fail "--service-path requires a value"

            SERVICE_PATH="$2"
            SERVICE_PATH_EXPLICIT=1
            shift 2
            ;;

        --dev)
            INSTALL_DEV=1
            shift
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


if ! [[ "${SERVICE_NAME}" =~ ^[A-Za-z0-9_.@-]+$ ]]; then
    fail "Service name contains invalid characters."
fi


[[ -d "${PROJECT_DIR}/app" ]] \
    || fail "Application directory not found: ${PROJECT_DIR}/app"

[[ -f "${PROJECT_DIR}/app/cli.py" ]] \
    || fail "CLI not found: ${PROJECT_DIR}/app/cli.py"

[[ -f "${PROJECT_DIR}/requirements.txt" ]] \
    || fail "requirements.txt was not found."

if (( INSTALL_DEV == 1 )); then
    [[ -f "${PROJECT_DIR}/requirements-dev.txt" ]] \
        || fail "requirements-dev.txt was not found."
fi


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


[[ -n "${CODEX_EXECUTABLE}" ]] \
    || fail "Codex CLI was not found."

[[ -x "${CODEX_EXECUTABLE}" ]] \
    || fail "Codex executable is not executable: ${CODEX_EXECUTABLE}"


command -v systemd-analyze >/dev/null 2>&1 \
    || fail "systemd-analyze was not found."

if (( APPLY == 1 )); then
    command -v systemctl >/dev/null 2>&1 \
        || fail "systemctl was not found."

    command -v sudo >/dev/null 2>&1 \
        || fail "sudo was not found."
fi


NEEDS_BOOTSTRAP=0

if [[ ! -x "${PYTHON_EXECUTABLE}" ]]; then
    if (( PYTHON_EXPLICIT == 1 )); then
        fail "Python executable not found: ${PYTHON_EXECUTABLE}"
    fi

    NEEDS_BOOTSTRAP=1

    [[ -n "${BOOTSTRAP_PYTHON}" ]] \
        || fail "python3 was not found."

    [[ -x "${BOOTSTRAP_PYTHON}" ]] \
        || fail "Bootstrap Python is not executable: ${BOOTSTRAP_PYTHON}"
fi


cd "${PROJECT_DIR}"


if (( NEEDS_BOOTSTRAP == 1 )); then
    if (( APPLY == 0 )); then
        info "Virtual environment is not present"

        echo
        echo "Dry run will not create:"
        echo "  ${VENV_DIR}"
        echo
        echo "On --apply the installer would:"
        echo "  1. Create the virtual environment"
        echo "  2. Upgrade pip"
        echo "  3. Install application dependencies"
        echo
    else
        info "Creating virtual environment"

        if ! "${BOOTSTRAP_PYTHON}" \
            -m venv \
            "${VENV_DIR}"
        then
            echo >&2
            echo "Unable to create the Python virtual environment." >&2
            echo >&2
            echo "On Debian/Ubuntu, install the venv package if needed:" >&2
            echo "  sudo apt install python3-venv" >&2
            echo >&2
            exit 1
        fi

        ok "Virtual environment created: ${VENV_DIR}"

        PYTHON_EXECUTABLE="${VENV_DIR}/bin/python"
    fi
fi


if (( APPLY == 1 )); then
    [[ -x "${PYTHON_EXECUTABLE}" ]] \
        || fail "Python executable not found after bootstrap: ${PYTHON_EXECUTABLE}"

    info "Checking pip"

    if ! "${PYTHON_EXECUTABLE}" \
        -m pip \
        --version \
        >/dev/null 2>&1
    then
        fail "pip is unavailable in ${PYTHON_EXECUTABLE}"
    fi

    ok "pip is available"


    info "Upgrading pip"

    "${PYTHON_EXECUTABLE}" \
        -m pip \
        install \
        --upgrade \
        pip

    ok "pip upgraded"


    if (( INSTALL_DEV == 1 )); then
        REQUIREMENTS_FILE="${PROJECT_DIR}/requirements-dev.txt"
    else
        REQUIREMENTS_FILE="${PROJECT_DIR}/requirements.txt"
    fi

    info "Installing Python dependencies"

    "${PYTHON_EXECUTABLE}" \
        -m pip \
        install \
        -r "${REQUIREMENTS_FILE}"

    ok "Python dependencies installed"
fi


DOCTOR_PYTHON="${PYTHON_EXECUTABLE}"

if [[ ! -x "${DOCTOR_PYTHON}" ]]; then
    DOCTOR_PYTHON="${BOOTSTRAP_PYTHON}"
fi


[[ -n "${DOCTOR_PYTHON}" ]] \
    || fail "No usable Python executable was found."

[[ -x "${DOCTOR_PYTHON}" ]] \
    || fail "Doctor Python is not executable: ${DOCTOR_PYTHON}"


info "Running environment diagnostics"

CODEX_BIN="${CODEX_EXECUTABLE}" \
"${DOCTOR_PYTHON}" \
    -m app.doctor

ok "Environment diagnostics passed"


UNIT_FILE="$(
    mktemp \
        "/tmp/${SERVICE_NAME}.XXXXXX.service"
)"

VERIFY_UNIT_FILE="$(
    mktemp \
        "/tmp/${SERVICE_NAME}.verify.XXXXXX.service"
)"


cleanup() {
    rm -f \
        "${UNIT_FILE}" \
        "${VERIFY_UNIT_FILE}"
}


trap cleanup EXIT


if [[ -x "${PYTHON_EXECUTABLE}" ]]; then
    UNIT_PYTHON="${PYTHON_EXECUTABLE}"
else
    UNIT_PYTHON="${VENV_DIR}/bin/python"
fi


info "Generating systemd unit"

CODEX_QUOTA_HOST="${HOST}" \
CODEX_QUOTA_PORT="${PORT}" \
CODEX_QUOTA_SAMPLE_SECONDS="${SAMPLE_SECONDS}" \
CODEX_BIN="${CODEX_EXECUTABLE}" \
"${DOCTOR_PYTHON}" \
    -c '
import sys

from app.core.config import load_config
from app.systemd import render_systemd_unit

config = load_config()

print(
    render_systemd_unit(
        config,
        user=sys.argv[1],
        group=sys.argv[2],
        home=sys.argv[3],
        python_executable=sys.argv[4],
        codex_executable=sys.argv[5],
    ),
    end="",
)
' \
    "${SERVICE_USER}" \
    "${SERVICE_GROUP}" \
    "${SERVICE_HOME}" \
    "${UNIT_PYTHON}" \
    "${CODEX_EXECUTABLE}" \
    > "${UNIT_FILE}"


info "Validating systemd unit"

if [[ -x "${UNIT_PYTHON}" ]]; then
    cp \
        "${UNIT_FILE}" \
        "${VERIFY_UNIT_FILE}"
else
    CODEX_QUOTA_HOST="${HOST}" \
    CODEX_QUOTA_PORT="${PORT}" \
    CODEX_QUOTA_SAMPLE_SECONDS="${SAMPLE_SECONDS}" \
    CODEX_BIN="${CODEX_EXECUTABLE}" \
    "${DOCTOR_PYTHON}" \
        -c '
import sys

from app.core.config import load_config
from app.systemd import render_systemd_unit

config = load_config()

print(
    render_systemd_unit(
        config,
        user=sys.argv[1],
        group=sys.argv[2],
        home=sys.argv[3],
        python_executable=sys.argv[4],
        codex_executable=sys.argv[5],
    ),
    end="",
)
' \
        "${SERVICE_USER}" \
        "${SERVICE_GROUP}" \
        "${SERVICE_HOME}" \
        "${DOCTOR_PYTHON}" \
        "${CODEX_EXECUTABLE}" \
        > "${VERIFY_UNIT_FILE}"

    info "Using bootstrap Python for dry-run unit verification"
fi


systemd-analyze verify \
    "${VERIFY_UNIT_FILE}"

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
    echo "  Service:   ${SERVICE_NAME}"
    echo "  Project:   ${PROJECT_DIR}"
    echo "  User:      ${SERVICE_USER}"
    echo "  Group:     ${SERVICE_GROUP}"
    echo "  HOME:      ${SERVICE_HOME}"
    echo "  Venv:      ${VENV_DIR}"
    echo "  Python:    ${UNIT_PYTHON}"
    echo "  Bootstrap: ${BOOTSTRAP_PYTHON:-not required}"
    echo "  Codex:     ${CODEX_EXECUTABLE}"
    echo "  Host:      ${HOST}"
    echo "  Port:      ${PORT}"
    echo "  Sample:    ${SAMPLE_SECONDS}s"

    if (( INSTALL_DEV == 1 )); then
        echo "  Packages:  development"
    else
        echo "  Packages:  runtime"
    fi

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
echo "Python:"
echo "  ${PYTHON_EXECUTABLE}"
echo
echo "Useful commands:"
echo "  systemctl status ${SERVICE_NAME}"
echo "  sudo systemctl restart ${SERVICE_NAME}"
echo "  journalctl -u ${SERVICE_NAME} -f"
