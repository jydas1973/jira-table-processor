#!/usr/bin/env bash
# Stop the TriageX JIRA Dashboard.

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$DIR/.env"
PID_FILE="$DIR/.dashboard.pid"

# Read DASHBOARD_PORT from .env; fall back to 5000
PORT=$(grep -E '^DASHBOARD_PORT=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 | tr -d '[:space:]')
PORT="${PORT:-5000}"

# Find process by port — reliable regardless of how the server was started
PID=$(lsof -ti :"$PORT" 2>/dev/null || true)

if [ -z "$PID" ]; then
    echo "[TriageX] No server running on port $PORT"
    rm -f "$PID_FILE"
    exit 0
fi

kill "$PID"
echo "[TriageX] Stopped dashboard (PID $PID, port $PORT)"
rm -f "$PID_FILE"
