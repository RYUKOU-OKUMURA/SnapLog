#!/bin/bash
cd "$(dirname "$0")/.."
LAUNCH_LOG="${PWD}/.snaplog_launch.log"

if [ ! -f .pid ]; then
  echo "SnapLog is not running via start.sh"
  exit 0
fi

PID="$(cat .pid)"
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] stop.sh pid=$PID" >> "$LAUNCH_LOG"
  echo "SnapLog stopped (PID $PID)"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] stop.sh stale pid=$PID" >> "$LAUNCH_LOG"
  echo "Stale PID file; process not running (PID $PID)"
fi
rm -f .pid
