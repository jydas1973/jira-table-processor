#!/usr/bin/env bash
# Start the TriageX JIRA Dashboard in the background and open it in the browser.
# Handles dependency installation automatically on a fresh clone.

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$DIR/.env"
LOG_FILE="$DIR/.dashboard.log"
PID_FILE="$DIR/.dashboard.pid"

# ── 1. Python 3.8+ check ──────────────────────────────────────────────────────
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        version=$("$candidate" -c 'import sys; print(sys.version_info >= (3, 8))' 2>/dev/null)
        if [ "$version" = "True" ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "[TriageX] ERROR: Python 3.8 or higher is required but was not found."
    echo "[TriageX]        Install it from https://www.python.org/downloads/ and retry."
    exit 1
fi

echo "[TriageX] Python → $($PYTHON --version)"

# ── 2. .env check ─────────────────────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$DIR/.env.template" ]; then
        cp "$DIR/.env.template" "$ENV_FILE"
        echo "[TriageX] Created .env from .env.template."
        echo "[TriageX] ⚠  Open $ENV_FILE and set JIRA_API_TOKEN before the server can connect to JIRA."
    else
        echo "[TriageX] WARNING: No .env file found. The server will start but cannot connect to JIRA."
        echo "[TriageX]          Create $ENV_FILE with at least JIRA_API_TOKEN=<your-token>."
    fi
fi

# ── 3. Read port (after .env is guaranteed to exist or warned about) ──────────
PORT=$(grep -E '^DASHBOARD_PORT=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 | tr -d '[:space:]')
PORT="${PORT:-5000}"

# ── 4. Already running — nothing to do ────────────────────────────────────────
if lsof -ti :"$PORT" &>/dev/null; then
    echo "[TriageX] Dashboard is already running → http://localhost:$PORT"
    exit 0
fi

cd "$DIR"

# ── 5. Dependency setup ───────────────────────────────────────────────────────
if command -v uv &>/dev/null && [ -f "$DIR/pyproject.toml" ]; then
    # uv handles venv creation and syncing from uv.lock automatically via `uv run`
    echo "[TriageX] Runtime  → uv (dependencies managed automatically)"
    SERVER_CMD=(uv run python backend/app.py --port "$PORT")

elif [ -f "$DIR/.venv/bin/python" ]; then
    echo "[TriageX] Runtime  → existing .venv"
    SERVER_CMD=("$DIR/.venv/bin/python" backend/app.py --port "$PORT")

elif [ -f "$DIR/venv/bin/python" ]; then
    echo "[TriageX] Runtime  → existing venv"
    SERVER_CMD=("$DIR/venv/bin/python" backend/app.py --port "$PORT")

else
    # No venv found — create one and install dependencies
    echo "[TriageX] No virtual environment found. Creating .venv ..."
    "$PYTHON" -m venv "$DIR/.venv"
    echo "[TriageX] Installing dependencies from backend/requirements.txt ..."
    "$DIR/.venv/bin/pip" install --quiet --upgrade pip
    "$DIR/.venv/bin/pip" install --quiet -r "$DIR/backend/requirements.txt"
    echo "[TriageX] Dependencies installed ✓"
    SERVER_CMD=("$DIR/.venv/bin/python" backend/app.py --port "$PORT")
fi

# ── 6. Start server in background ─────────────────────────────────────────────
echo "[TriageX] Starting dashboard on port $PORT ..."
nohup "${SERVER_CMD[@]}" > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

# ── 7. Poll until the server responds (up to 15 seconds) ─────────────────────
echo -n "[TriageX] Waiting for server"
READY=0
for i in $(seq 1 30); do
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
    echo "[TriageX] Server did not respond within 15 seconds."
    echo "[TriageX] Check logs: $LOG_FILE"
    exit 1
fi

URL="http://localhost:$PORT"
echo "[TriageX] Dashboard → $URL"
echo "[TriageX] Logs      → $LOG_FILE  (PID $SERVER_PID)"

# ── 8. Open browser: macOS → Linux → fallback ─────────────────────────────────
if command -v open &>/dev/null; then
    open "$URL"
elif command -v xdg-open &>/dev/null; then
    xdg-open "$URL"
else
    echo "[TriageX] Open your browser and navigate to $URL"
fi
