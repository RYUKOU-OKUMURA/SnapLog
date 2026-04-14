#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

detect_python() {
  if [ -n "${SNAPLOG_PYTHON:-}" ] && [ -x "${SNAPLOG_PYTHON}" ]; then
    printf '%s\n' "${SNAPLOG_PYTHON}"
    return 0
  fi

  if [ -x "${PWD}/venv/bin/python" ]; then
    printf '%s\n' "${PWD}/venv/bin/python"
    return 0
  fi

  if [ -x "${PWD}/.venv/bin/python" ]; then
    printf '%s\n' "${PWD}/.venv/bin/python"
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi

  return 1
}

PYTHON_BIN="$(detect_python)" || {
  echo "Python interpreter not found. Set SNAPLOG_PYTHON or create venv/.venv." >&2
  exit 1
}

echo "Building SnapLog.app with: $PYTHON_BIN"
rm -rf build dist/SnapLog.app
"$PYTHON_BIN" setup.py py2app

APP_PATH="${PWD}/dist/SnapLog.app"
if [ ! -d "$APP_PATH" ]; then
  echo "Build finished but app bundle was not created: $APP_PATH" >&2
  exit 1
fi

echo "Built: $APP_PATH"
