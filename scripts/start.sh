#!/bin/bash
cd "$(dirname "$0")/.."
nohup python -m src.main > /dev/null 2>&1 &
echo $! > .pid
echo "SnapLog started with PID: $(cat .pid)"
