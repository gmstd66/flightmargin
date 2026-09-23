#!/usr/bin/env bash

set -euo pipefail


DEFAULT_SERVICE_NAME="codex-quota"
SERVICE_NAME="${DEFAULT_SERVICE_NAME}"

SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
SERVICE_PATH_EXPLICIT=0

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
    pwd
)"

PROJECT_DIR="$(
    cd -- "${SCRIPT_DIR}/.."
    pwd
)"

VENV_DIR="${PROJECT_DIR}/venv"
DATA_DIR="${PROJECT_DIR}/data"

APPLY=0
REMOVE_VENV=0
REMOVE_DATA=0


usage() {
    cat <<EOF
Codex Quota Monitor Linux uninstaller

Usage:
  scripts/uninstall-linux.sh [options]

Options:
  --service-name NAME
      Systemd service name.

      Default:
        ${SERVICE_NAME}

  --apply
      Perform the uninstall.

  --dry-run
      Show what would be removed.
      This is the default.

  --remove-venv
      Also remove:
        ${VENV_DIR}

  --remove-data
      Also remove:
        ${DATA_DIR}

      WARNING:
      This may permanently delete quota history.

  --service-path PATH
      Systemd service unit to remove.

      Default:
        /etc/systemd/system/<service-name>.service

  -h, --help
      Show this help.

By default the script removes only the selected
systemd service. The repository, virtual environment,
runtime data, Codex CLI, and Codex authentication
are preserved.
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

        --apply)
            APPLY=1
            shift
            ;;

        --dry-run)
            APPLY=0
            shift
            ;;

        --remove-venv)
            REMOVE_VENV=1
            shift
            ;;

        --remove-data)
            REMOVE_DATA=1
            shift
            ;;

        --service-path)
            [[ $# -ge 2 ]] \
                || fail "--service-path requires a value"

            SERVICE_PATH="$2"
            SERVICE_PATH_EXPLICIT=1
            shift 2
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
    fail "This uninstaller currently supports Linux only."
fi


if ! [[ "${SERVICE_NAME}" =~ ^[A-Za-z0-9_.@-]+$ ]]; then
    fail "Service name contains invalid characters."
fi


if (( APPLY == 0 )); then
    echo "Codex Quota Monitor uninstall dry run"
    echo
    echo "Service:"
    echo "  ${SERVICE_NAME}"

    echo
    echo "Would remove systemd service:"
    echo "  ${SERVICE_PATH}"

    echo
    echo "Would preserve repository:"
    echo "  ${PROJECT_DIR}"

    if (( REMOVE_VENV == 1 )); then
        echo
        echo "Would remove virtual environment:"
        echo "  ${VENV_DIR}"
    else
        echo
        echo "Would preserve virtual environment:"
        echo "  ${VENV_DIR}"
    fi

    if (( REMOVE_DATA == 1 )); then
        echo
        echo "Would remove runtime data:"
        echo "  ${DATA_DIR}"
    else
        echo
        echo "Would preserve runtime data:"
        echo "  ${DATA_DIR}"
    fi

    echo
    echo "No system changes were made."

    exit 0
fi


command -v sudo >/dev/null 2>&1 \
    || fail "sudo was not found."

command -v systemctl >/dev/null 2>&1 \
    || fail "systemctl was not found."


if systemctl list-unit-files \
    "${SERVICE_NAME}.service" \
    --no-legend \
    2>/dev/null \
    | grep -q "^${SERVICE_NAME}.service"
then
    info "Stopping and disabling service"

    sudo systemctl disable \
        --now \
        "${SERVICE_NAME}" \
        >/dev/null 2>&1 \
        || true
fi


if sudo test -f "${SERVICE_PATH}"; then
    info "Removing systemd service"

    sudo rm -f \
        "${SERVICE_PATH}"

    ok "Removed ${SERVICE_PATH}"
else
    info "Systemd service file is already absent"
fi


info "Reloading systemd"

sudo systemctl daemon-reload

sudo systemctl reset-failed \
    "${SERVICE_NAME}" \
    >/dev/null 2>&1 \
    || true


if (( REMOVE_VENV == 1 )); then
    if [[ -d "${VENV_DIR}" ]]; then
        info "Removing virtual environment"

        rm -rf \
            "${VENV_DIR}"

        ok "Removed ${VENV_DIR}"
    else
        info "Virtual environment already absent"
    fi
fi


if (( REMOVE_DATA == 1 )); then
    if [[ -d "${DATA_DIR}" ]]; then
        info "Removing runtime data"

        rm -rf \
            "${DATA_DIR}"

        ok "Removed ${DATA_DIR}"
    else
        info "Runtime data already absent"
    fi
fi


echo
echo "Codex Quota Monitor service removed."
echo
echo "Service:"
echo "  ${SERVICE_NAME}"

if (( REMOVE_VENV == 0 )); then
    echo
    echo "Virtual environment preserved:"
    echo "  ${VENV_DIR}"
fi

if (( REMOVE_DATA == 0 )); then
    echo
    echo "Runtime data preserved:"
    echo "  ${DATA_DIR}"
fi

echo
echo "Repository preserved:"
echo "  ${PROJECT_DIR}"
