#!/bin/bash
cd "$(dirname "$0")/.."
MODE="${1:-headless}"
LAUNCH_LOG="${PWD}/.snaplog_launch.log"

detect_python() {
  if [ -n "${SNAPLOG_PYTHON:-}" ] && [ -x "${SNAPLOG_PYTHON}" ]; then
    printf '%s\n' "${SNAPLOG_PYTHON}"
    return 0
  fi

  if [ -x "${PWD}/.venv/bin/python" ]; then
    printf '%s\n' "${PWD}/.venv/bin/python"
    return 0
  fi

  if [ -x "${PWD}/venv/bin/python" ]; then
    printf '%s\n' "${PWD}/venv/bin/python"
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi

  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi

  return 1
}

usage() {
  echo "Usage: $0 [headless|desktop]" >&2
  echo "  headless (default) - main loop only (unchanged from before)" >&2
  echo "  desktop            - menu bar UI; grant Screen Recording to this app (Terminal/python)" >&2
  exit 1
}

if [ -f .pid ]; then
  PID="$(cat .pid)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "SnapLog is already running (PID $PID)"
    exit 0
  fi
  echo "Removing stale PID file: $PID"
  rm -f .pid
fi

PYTHON_BIN="$(detect_python)" || {
  echo "Python interpreter not found. Set SNAPLOG_PYTHON or create .venv/venv." >&2
  exit 1
}

mkdir -p "$(dirname "$LAUNCH_LOG")"
{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] start.sh mode=$MODE"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] python=$PYTHON_BIN"
} >> "$LAUNCH_LOG"

case "$MODE" in
  -h|--help|help)
    usage
    ;;
  desktop|menu-bar|menubar)
    nohup env PYTHONUNBUFFERED=1 "$PYTHON_BIN" -m src.main --menu-bar >> "$LAUNCH_LOG" 2>&1 &
    echo "Menu bar mode. Bootstrap log: $LAUNCH_LOG"
    ;;
  headless)
    nohup env PYTHONUNBUFFERED=1 "$PYTHON_BIN" -m src.main >> "$LAUNCH_LOG" 2>&1 &
    echo "Headless (main loop only)"
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    usage
    ;;
esac

PID="$!"
echo "$PID" > .pid

sleep 1
if ! kill -0 "$PID" 2>/dev/null; then
  echo "SnapLog failed to stay running. Check $LAUNCH_LOG"
  rm -f .pid
  exit 1
fi

echo "SnapLog started with PID: $PID"
