#!/bin/bash
cd "$(dirname "$0")/.."
if [ -f .pid ]; then
    kill $(cat .pid)
    rm .pid
    echo "SnapLog stopped"
else
    echo "SnapLog is not running"
fi

