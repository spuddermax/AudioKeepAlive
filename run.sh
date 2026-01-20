#!/bin/bash
# Launcher script for Audio Keep-Alive
# Uses the virtual environment if it exists, otherwise uses system Python

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -d "$SCRIPT_DIR/venv" ]; then
	"$SCRIPT_DIR/venv/bin/python" "$SCRIPT_DIR/main.py" "$@"
else
	python3 "$SCRIPT_DIR/main.py" "$@"
fi
