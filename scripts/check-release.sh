#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
    pwd
)"

PROJECT_DIR="$(
    cd -- "${SCRIPT_DIR}/.."
    pwd
)"

PYTHON_EXECUTABLE="${PYTHON:-python3}"
PORT="${CODEX_QUOTA_RELEASE_PORT:-18097}"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/codex-quota-release.XXXXXX")"
VENV_DIR="${WORK_DIR}/venv"
DATA_DIR="${WORK_DIR}/data"
SERVER_LOG="${WORK_DIR}/server.log"
SERVER_PID=""

cleanup() {
    if [[ -n "${SERVER_PID}" ]] && kill -0 "${SERVER_PID}" 2>/dev/null; then
        kill "${SERVER_PID}" 2>/dev/null || true
        wait "${SERVER_PID}" 2>/dev/null || true
    fi
    rm -rf -- "${WORK_DIR}"
}

trap cleanup EXIT

[[ -x "${PYTHON_EXECUTABLE}" ]] \
    || { echo "ERROR: Python executable not found: ${PYTHON_EXECUTABLE}" >&2; exit 1; }

if ! [[ "${PORT}" =~ ^18[0-9]{3}$ ]] || (( PORT < 18000 || PORT > 18999 )); then
    echo "ERROR: CODEX_QUOTA_RELEASE_PORT must be in 18000-18999" >&2
    exit 1
fi

"${PYTHON_EXECUTABLE}" -m pytest -v
PYTHON="${PYTHON_EXECUTABLE}" "${SCRIPT_DIR}/build-release.sh"
"${PYTHON_EXECUTABLE}" "${SCRIPT_DIR}/verify-release.py" "${PROJECT_DIR}/dist"

WHEEL_PATH="$(find "${PROJECT_DIR}/dist" -maxdepth 1 -type f -name '*.whl')"

"${PYTHON_EXECUTABLE}" -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install "${WHEEL_PATH}"

installed_path="$(
    cd "${WORK_DIR}"
    "${VENV_DIR}/bin/python" -c \
        'from pathlib import Path; import app; print(Path(app.__file__).resolve())'
)"

case "${installed_path}" in
    "${VENV_DIR}"/lib/*/site-packages/app/__init__.py) ;;
    *)
        echo "ERROR: app imported outside site-packages: ${installed_path}" >&2
        exit 1
        ;;
esac

expected_version="$(
    "${PYTHON_EXECUTABLE}" -c 'from app.version import __version__; print(__version__)'
)"

actual_version="$(
    cd "${WORK_DIR}"
    "${VENV_DIR}/bin/codex-quota" --version
)"

[[ "${actual_version}" == "codex-quota-monitor ${expected_version}" ]] \
    || { echo "ERROR: unexpected CLI version: ${actual_version}" >&2; exit 1; }

export CODEX_QUOTA_DATA_DIR="${DATA_DIR}"
export CODEX_QUOTA_DB="${DATA_DIR}/quota.db"
export CODEX_QUOTA_HOST="127.0.0.1"
export CODEX_QUOTA_PORT="${PORT}"

(
    cd "${WORK_DIR}"
    "${VENV_DIR}/bin/codex-quota" doctor
)
(
    cd "${WORK_DIR}"
    "${VENV_DIR}/bin/codex-quota" status
)

(
    cd "${WORK_DIR}"
    "${VENV_DIR}/bin/codex-quota" serve >"${SERVER_LOG}" 2>&1
) &
SERVER_PID="$!"

health_url="http://127.0.0.1:${PORT}/api/health"
for _ in {1..20}; do
    if curl --fail --silent --show-error "${health_url}" > /dev/null; then
        break
    fi
    sleep 1
done

curl --fail --silent --show-error "${health_url}" > /dev/null
curl --fail --silent --show-error "http://127.0.0.1:${PORT}/" > /dev/null
curl --fail --silent --show-error "http://127.0.0.1:${PORT}/static/app.css" > /dev/null
curl --fail --silent --show-error "http://127.0.0.1:${PORT}/static/app.js" > /dev/null

[[ -f "${DATA_DIR}/quota.db" ]] \
    || { echo "ERROR: isolated test database was not created" >&2; exit 1; }

echo "Isolated installed-wheel validation passed: ${WHEEL_PATH}"
