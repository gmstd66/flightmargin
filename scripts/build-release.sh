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
DIST_DIR="${PROJECT_DIR}/dist"

[[ -x "${PYTHON_EXECUTABLE}" ]] \
    || { echo "ERROR: Python executable not found: ${PYTHON_EXECUTABLE}" >&2; exit 1; }

rm -rf -- "${DIST_DIR}"
mkdir -p -- "${DIST_DIR}"

"${PYTHON_EXECUTABLE}" -m pip wheel \
    --no-deps \
    --wheel-dir "${DIST_DIR}" \
    "${PROJECT_DIR}"

wheel_count="$(find "${DIST_DIR}" -maxdepth 1 -type f -name '*.whl' | wc -l)"

[[ "${wheel_count}" == "1" ]] \
    || { echo "ERROR: Expected exactly one wheel in ${DIST_DIR}" >&2; exit 1; }

wheel_path="$(find "${DIST_DIR}" -maxdepth 1 -type f -name '*.whl')"

echo "Built release artifact: ${wheel_path}"
