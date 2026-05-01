# TriageX JIRA Dashboard

An interactive web dashboard for Oracle ExaInfra on-call engineers to query JIRA, visualise triage success rates, and email status reports — no Python scripts or static HTML files required.

---

## Overview

The TriageX JIRA Dashboard connects to `jira-sd.mc1.oracleiaas.com` via a personal API token and provides:

- **Date-range picker** that drives a JQL query against JIRA and fetches all tickets labelled `oneview_triagex_success` or `oneview_triagex_failed`
- **Summary cards** — Total Triaged, Successful count, Success Rate %
- **Weekly success rate line chart** — one data point per calendar week in the selected range
- **Paginated issue table** — JIRA ID (clickable), Status badge, Date Created, optional Report link and Log Files
- **Optional "Include Report Links"** — fetches VoxioTriageX report URLs and log filenames per ticket (one extra JIRA API call per ticket)
- **Email Report panel** — send the first 50 issues as a styled HTML email via the Oracle internal SMTP relay

---

## Prerequisites

- Python 3.8 or higher (`python --version`)
- Network access to `https://jira-sd.mc1.oracleiaas.com`
- A personal JIRA API token (instructions below)

---

## How to Generate a JIRA API Token

These steps are for the Oracle self-hosted JIRA instance at `https://jira-sd.mc1.oracleiaas.com` (not Atlassian Cloud).

1. Log in to `https://jira-sd.mc1.oracleiaas.com` in your browser.
2. Click your **profile avatar** (top-right corner) → **Profile**.
3. In the left sidebar, click **Personal Access Tokens** (or navigate directly to `https://jira-sd.mc1.oracleiaas.com/secure/ViewProfile.jspa?selectedTab=com.atlassian.pats.pats-plugin:jira-user-personal-access-tokens`).
4. Click **Create token**.
5. Give it a name (e.g., `triagex-dashboard`) and optionally set an expiry date.
6. Click **Create** and **copy the token immediately** — it is only shown once.
7. Paste it as `JIRA_API_TOKEN=<token>` in `triagex-jira-dashboard/.env`.

> **Note:** If you cannot find Personal Access Tokens in your profile, contact your JIRA administrator — some self-hosted instances require administrator enablement of the PAT feature.

---

## Installation & Setup

Two installation methods are supported: **uv** (recommended — fast, no manual venv management) and **pip** (standard).

---

### Method 1 — uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager. It reads `pyproject.toml`, pins all dependencies in `uv.lock`, and manages the virtual environment automatically.

**Install uv** (if not already installed):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS / Linux
# Or via Homebrew:
brew install uv
```

**Set up and run:**

```bash
# 1. Enter the project directory
cd triagex-jira-dashboard

# 2. Copy the environment template
cp .env.template .env

# 3. Edit .env and add your JIRA API token
# Open .env in your editor and replace "your_personal_api_token_here"

# 4. Install all dependencies (creates .venv automatically from pyproject.toml + uv.lock)
uv sync

# 5. Start the dashboard
uv run python backend/app.py
```

`uv sync` reads the pinned `uv.lock` file and installs an exact, reproducible environment in `.venv/` — no manual venv activation required.

---

### Method 2 — pip (Standard)

```bash
# 1. Enter the project directory
cd triagex-jira-dashboard

# 2. Copy the environment template
cp .env.template .env

# 3. Edit .env and add your JIRA API token
# Open .env in your editor and replace "your_personal_api_token_here"

# 4. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# 5. Install dependencies
pip install -r backend/requirements.txt

# 6. Start the dashboard
python backend/app.py
```

---

## Running the Server

### With uv

```bash
# Start server only (open browser manually at http://localhost:5000)
uv run python backend/app.py

# Start server AND auto-open browser
uv run python backend/app.py --open

# Use a custom port
uv run python backend/app.py --port 8080

# Custom port + auto-open
uv run python backend/app.py --port 8080 --open
```

### With pip (venv activated)

```bash
# Start server only
python backend/app.py

# Start server AND auto-open browser
python backend/app.py --open

# Use a custom port
python backend/app.py --port 8080

# Custom port + auto-open
python backend/app.py --port 8080 --open
```

---

## Stopping the Server

### Interactive terminal (both uv and pip)

If the server is running in the foreground, press **Ctrl + C** in the terminal where it is running.

### Background process — find and kill by port

If you started the server in the background (e.g. with `&`) or cannot find the terminal, use the port number to locate and stop it:

```bash
# macOS / Linux — find the PID listening on port 5000 (or your custom port)
lsof -ti :5000 | xargs kill

# If the process does not respond to a normal kill, force it:
lsof -ti :5000 | xargs kill -9

# Windows (Command Prompt / PowerShell) — find the PID
netstat -ano | findstr :5000
# Then kill it (replace <PID> with the number from the output above)
taskkill /PID <PID> /F
```

> **Tip:** If you used `--port 8080` (or another custom port), replace `5000` with that port number in the commands above.

---

## Using the Dashboard

1. Open `http://localhost:5000` in your browser.
2. Use the **date shortcuts** (Last 7d / 14d / 30d / 90d) or pick custom **From / To** dates using the calendar pickers.
3. Click **Advanced Options** to inspect or modify the JQL query, change Max Results, or enable **Include Report Links** (fetches VoxioTriageX report URLs — slower).
4. Click **Analyze**. A loading spinner appears while JIRA is queried.
5. Results appear:
   - **Summary cards**: Total Triaged, Successful count, Success Rate %.
   - **Weekly Success Rate chart**: one data point per calendar week in the date range.
   - **JIRA Status Report table**: all triaged tickets with status badges.
     - Use the **Rows per page** dropdown (10 / 25 / 50 / 100) above the table.
     - Navigate pages using the pagination controls below the table.
     - Click any **JIRA ID** to open the ticket in a new browser tab.
     - If Report Links were fetched, click **Report** to open the VoxioTriageX triage report.

---

## Emailing a Report

1. Run an analysis (click **Analyze**) until results appear.
2. Click **Email This Report** to expand the email panel.
3. Check one or more recipient boxes. Use **Select All** or **Clear** as needed.
4. Edit the **Subject** line if desired (auto-includes the date range you selected).
5. Click **Send Report**. A confirmation or error message appears inline.
6. To send to a different set of recipients, uncheck/recheck and click **Send Report** again.

> **Note:** Email uses the Oracle internal SMTP relay (`EMAIL_SMTP_SERVER`). This only works on the corporate network or VPN. No authentication is required.

---

## Functionality Details

- **Label logic**: A ticket is classified as `Success` if its JIRA labels contain `oneview_triagex_success`; as `Failed` if they contain `oneview_triagex_failed`. Tickets with neither label are excluded from the report.
- **Date range**: When both dates are filled, any existing `created >=` or `created <=` condition in the JQL is automatically removed and replaced by the picker values. If no dates are selected, the JQL is sent as-is.
- **Max Results**: JIRA API maximum is 1000 per query. For large date ranges, increase this value in Advanced Options. The default is 500.
- **Email Report**: The first 50 issues from the current analysis are sent as a styled HTML email. The Log Files column in the email shows a file count badge rather than full filenames to keep the email compact. Re-running Analyze replaces the buffered results; the Send button always reflects the latest analysis.
- **Known limitation**: The last analysis result is stored in a module-level variable (`_last_status_df`). This is shared state and is not safe for multi-worker deployments, but is acceptable for this single-user on-call tool.

---

## Configuration Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `JIRA_URL` | No | `https://jira-sd.mc1.oracleiaas.com` | JIRA instance URL |
| `JIRA_API_TOKEN` | **Yes** | — | Personal JIRA API token |
| `JQL_QUERY` | No | See template | Default JQL shown in the editor |
| `DASHBOARD_PORT` | No | `5000` | Port for the web server |
| `EMAIL_SMTP_SERVER` | No* | — | Internal SMTP relay hostname |
| `EMAIL_FROM` | No* | — | Sender email address |
| `EMAIL_TO` | No* | — | Comma-separated recipient pool |
| `EMAIL_SUBJECT` | No | `TriageX JIRA Analysis Report` | Default email subject |

*Required only if you use the Email Report feature.

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `JIRA_API_TOKEN is not configured` | .env not created or token missing | Copy `.env.template` to `.env` and add token |
| `Failed to connect to JIRA` | Wrong token or no network access | Verify token; check VPN |
| `JQL query appears invalid` | Empty or malformed JQL | Check the JQL in Advanced Options |
| `No issues found` | JQL returns 0 results in date range | Widen date range or adjust JQL |
| Port already in use | Another process on port 5000 | Use `--port 8080` |
| Chart shows "not enough data" | All issues fall within a single calendar week | Widen date range |
| `No analysis results available` | Send clicked before Analyze | Run Analyze first |
| `EMAIL_SMTP_SERVER is not configured` | Email vars missing from .env | Add `EMAIL_*` vars to `.env` |
| Email not delivered | Off VPN or SMTP relay unreachable | Connect to Oracle network or VPN |
| Send button stays disabled | No recipients checked | Check at least one recipient |
| `uv: command not found` | uv not installed | Run `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `uv sync` fails | Python version < 3.8 | Upgrade Python or install via `uv python install 3.12` |
