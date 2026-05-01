#!/usr/bin/env bash
# Start the TriageX JIRA Dashboard in the background and open it in the browser.

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$DIR/.env"
LOG_FILE="$DIR/.dashboard.log"
PID_FILE="$DIR/.dashboard.pid"

# Read DASHBOARD_PORT from .env; fall back to 5000
PORT=$(grep -E '^DASHBOARD_PORT=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 | tr -d '[:space:]')
PORT="${PORT:-5000}"

# Already running — nothing to do
if lsof -ti :"$PORT" &>/dev/null; then
    echo "[TriageX] Dashboard is already running → http://localhost:$PORT"
    exit 0
fi

cd "$DIR"

# Select runtime: uv (preferred) → .venv → venv → system python3
if command -v uv &>/dev/null && [ -f "$DIR/pyproject.toml" ]; then
    SERVER_CMD=(uv run python backend/app.py --port "$PORT")
elif [ -f "$DIR/.venv/bin/python" ]; then
    SERVER_CMD=("$DIR/.venv/bin/python" backend/app.py --port "$PORT")
elif [ -f "$DIR/venv/bin/python" ]; then
    SERVER_CMD=("$DIR/venv/bin/python" backend/app.py --port "$PORT")
else
    SERVER_CMD=(python3 backend/app.py --port "$PORT")
fi

echo "[TriageX] Starting dashboard on port $PORT ..."
nohup "${SERVER_CMD[@]}" > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

# Poll until the server responds (up to 10 seconds)
echo -n "[TriageX] Waiting for server"
READY=0
for i in $(seq 1 20); do
    sleep 0.5
    if curl -s "http://localhost:$PORT" &>/dev/null; then
        READY=1
        echo " ready!"
        break
    fi
    echo -n "."
done

if [ "$READY" -eq 0 ]; then
    echo ""
    echo "[TriageX] Server did not respond within 10 seconds."
    echo "[TriageX] Check logs: $LOG_FILE"
    exit 1
fi

URL="http://localhost:$PORT"
echo "[TriageX] Dashboard → $URL"
echo "[TriageX] Logs      → $LOG_FILE  (PID $SERVER_PID)"

# Open browser: macOS (open) → Linux (xdg-open) → fallback message
if command -v open &>/dev/null; then
    open "$URL"
elif command -v xdg-open &>/dev/null; then
    xdg-open "$URL"
else
    echo "[TriageX] Open your browser and navigate to $URL"
fi
