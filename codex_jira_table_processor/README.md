# JIRA Codex SDK Harness

A TypeScript harness that uses the OpenAI Codex SDK (`@openai/codex-sdk`) to orchestrate a
Codex agent that fetches JIRA issues, analyzes labels, and generates status reports — all driven
by a single command.

---

## What This Application Does

This harness wraps the existing Python script `jira_table_analyze.py` with a Codex SDK
orchestration layer. Instead of running the Python script directly, you run a single TypeScript
entry point that:

1. Reads your JIRA credentials and JQL query from `.env`
2. Sends a structured prompt to a Codex agent (`oca/gpt-5.3-codex`)
3. Streams the agent's shell commands to your terminal in real time
4. The agent activates the Python virtual environment and executes the analysis script
5. Reports success or failure with a duration summary

The Python script (`jira_table_analyze.py`) and its virtual environment (`report_env/`) are
never modified — this harness only drives them.

---

## Prerequisites

### 1. Bun (JavaScript/TypeScript runtime)

```bash
curl -fsSL https://bun.sh/install | bash
# Restart your terminal after install
bun --version   # verify: >= 1.0
```

### 2. Codex CLI + Authentication

The Codex SDK reads credentials from your Codex CLI config at `~/.codex/config.toml`.
Your environment is already configured to use Oracle Code Assist (OCA):

```toml
profile = "gpt-5-codex"

[profiles.gpt-5-codex]
model = "oca/gpt-5.3-codex"
model_provider = "oca_responses"
```

If you have not authenticated yet:

```bash
codex auth login
```

### 3. Python Virtual Environment

The Python venv `report_env/` must exist at the project root with all dependencies installed.
If it is missing:

```bash
# From the project root (one level up)
cd ..
python3 -m venv report_env
source report_env/bin/activate
pip install -r requirements.txt
deactivate
cd codex_jira_table_processor
```

### 4. `.env` File

A `.env` symlink inside this folder points to the project root `.env`.
If it is missing, create it:

```bash
ln -s ../.env .env
```

The project root `.env` must contain at minimum:

```env
JIRA_URL=https://jira-sd.mc1.oracleiaas.com
JIRA_API_TOKEN=your_jira_api_token_here
JQL_QUERY='project in (DBAASOPS,EXACSOPS,EXACCOPS) AND labels = oneview_triagex_inprogress AND created >= -10d'
```

See `.env.template` at the project root for all available variables.

### 5. Install Node Dependencies

```bash
cd codex_jira_table_processor
bun install
```

---

## Configuration

All configuration is read from `.env` (symlinked from the project root):

| Variable | Required | Default | Description |
|---|---|---|---|
| `JIRA_URL` | No | `https://jira-sd.mc1.oracleiaas.com` | JIRA instance URL |
| `JIRA_API_TOKEN` | **Yes** | — | JIRA personal API token |
| `JQL_QUERY` | No | ExaInfra patching failures (last 3d) | JQL filter string |
| `MAX_RESULTS` | No | `100` | Maximum issues to fetch |
| `EMAIL_SMTP_SERVER` | No | — | SMTP hostname (port 25, no TLS) |
| `EMAIL_FROM` | No | — | Sender email address |
| `EMAIL_TO` | No | — | Comma-separated recipient addresses |
| `EMAIL_SUBJECT` | No | `JIRA Status Report` | Email subject prefix |

If `EMAIL_SMTP_SERVER`, `EMAIL_FROM`, and `EMAIL_TO` are all set, the HTML report is emailed
after generation. Otherwise the email step is skipped silently.

If the JQL query contains a relative date filter like `created >= -3d`, the email subject is
automatically extended with the exact date range, e.g.:
`TriageX JIRA Analysis Report from Apr 4, 2026 to Apr 7, 2026`

---

## Quick Start

All commands must be run from inside this folder (`codex_jira_table_processor/`):

```bash
cd codex_jira_table_processor

# Standard run
bun run codex-harness/index.ts

# With detailed report (fetches VoxioTriageX report URLs + log file names per ticket)
bun run codex-harness/index.ts --detailed-report

# Using npm scripts
bun run analyze
bun run analyze:detailed
```

### Output Files

Output files are written to the `reports/` directory **inside this folder**
(`codex_jira_table_processor/reports/`). Open them directly from here after a run.

| File | Description |
|---|---|
| `reports/jira_table.csv` | All fetched JIRA issues — raw data, all columns |
| `reports/jira_status_report.csv` | Filtered report — only Success/Failed tickets |
| `reports/jira_status_report.html` | Styled interactive HTML with clickable JIRA links |

With `--detailed-report`, the HTML also includes Report Link and Log Files columns per ticket.

---

## Process Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│  codex-harness/index.ts  (entry point)                              │
│                                                                     │
│  1. Parse CLI args  ──── --detailed-report flag                     │
│  2. Load .env  ────────  JIRA_URL, JIRA_API_TOKEN, JQL_QUERY, ...  │
│  3. Validate  ─────────  exit(1) if JIRA_API_TOKEN missing          │
│  4. Build email subject  append date range if JQL has created >= -Nd│
│  5. Assemble AnalyzerConfig (jiraUrl, apiToken, jqlQuery,           │
│                              maxResults, detailedReport, workDir,    │
│                              emailConfig?)                           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  calls runAnalyzer(config)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  codex-harness/analyzer.ts  (Codex SDK orchestration)               │
│                                                                     │
│  6. Build full prompt                                               │
│        = JIRA_ANALYZER_SYSTEM_PROMPT                                │
│          + "---"                                                     │
│          + task parameters (URL, JQL, flags, email config)          │
│                                                                     │
│  7. new Codex()                                                     │
│     codex.startThread({                                             │
│       workingDirectory: project root,                               │
│       sandboxMode: "danger-full-access",   ← grants all tools       │
│       model: "oca/gpt-5.3-codex",                                  │
│       approvalPolicy: "never",                                      │
│     })                                                              │
│                                                                     │
│  8. thread.runStreamed(fullPrompt)  ← streaming begins              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  event stream
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Codex Agent  (oca/gpt-5.3-codex, workDir = codex_jira_table_processor/)  │
│                                                                     │
│  9.  source ../report_env/bin/activate                              │
│  10. python3 ../jira_table_analyze.py [--detailed-report]          │
│        │                                                            │
│        ├─ Connect to JIRA API with JIRA_URL + JIRA_API_TOKEN       │
│        ├─ Execute JQL query, fetch up to MAX_RESULTS issues         │
│        ├─ [--detailed-report] Fetch remote links per ticket         │
│        │    (VoxioTriageX report URL + log file names)              │
│        ├─ Analyse labels per ticket:                                │
│        │    oneview_triagex_success  →  Status: Success             │
│        │    oneview_triagex_failed   →  Status: Failed              │
│        ├─ Write reports/jira_table.csv          (codex_jira_table_processor/reports/)  │
│        ├─ Write reports/jira_status_report.csv  (codex_jira_table_processor/reports/)  │
│        ├─ Write reports/jira_status_report.html (codex_jira_table_processor/reports/)  │
│        └─ [email configured] Send HTML report via SMTP              │
│                                                                     │
│  11. Agent outputs completion JSON:                                 │
│        { "success": true, "files": [...], "emailSent": false }      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  events: item.completed / turn.completed
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Back in analyzer.ts — event loop                                   │
│                                                                     │
│  item.completed / agent_message    → accumulate fullResponse        │
│  item.completed / command_execution → print [AGENT] Command: ...   │
│  turn.completed                    → log tokens, break  ← CRITICAL │
│  error                             → log [AGENT] Stream error       │
│                                                                     │
│  12. Parse fullResponse → AnalyzerResult                            │
│        Strategy 1: last JSON code block in response                 │
│        Strategy 2: inline {...} containing "success"                │
│        Strategy 3: infer from text ("analysis complete")            │
│        Fallback:   { success: false, outputFiles: [] }              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  returns AnalyzerResult
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Back in index.ts                                                   │
│                                                                     │
│  13. Print duration + output file list                              │
│  14. process.exit(0)  on success                                    │
│      process.exit(1)  on failure                                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
codex_jira_table_processor/
├── .env                    → symlink to ../.env
├── package.json            bun project manifest
├── tsconfig.json           TypeScript config (strict, verbatimModuleSyntax)
├── shared/
│   ├── config.ts           CODEX_MODEL, CODEX_NETWORK_ACCESS, DEFAULT_CONFIG
│   ├── types.ts            AnalyzerConfig, EmailConfig, AnalyzerResult
│   └── prompts.ts          JIRA_ANALYZER_SYSTEM_PROMPT
└── codex-harness/
    ├── index.ts            CLI entry point — arg parsing, env, orchestration
    └── analyzer.ts         Codex SDK agent — runStreamed() event loop
```

---

## Troubleshooting

**Process hangs after the agent finishes (~90 seconds)**
The `break` on `turn.completed` is missing or unreachable in `analyzer.ts`. Verify it is
present inside the `else if (event.type === "turn.completed")` branch.

**`ERROR: JIRA_API_TOKEN is not set`**
Add `JIRA_API_TOKEN=your_token` to the project root `.env` file.

**`new Codex()` auth error / 401**
Run `codex auth login` to re-authenticate, or verify `~/.codex/config.toml` has the correct
`model_provider` base URL and your OCA credentials are valid.

**`bun: command not found`**
Install Bun: `curl -fsSL https://bun.sh/install | bash`, then restart your terminal.

**Agent cannot find `../jira_table_analyze.py`**
The harness sets `workDir = resolve(".")` (= `codex_jira_table_processor/`). The agent uses
`../jira_table_analyze.py` and `../report_env/` relative to that directory.
Ensure you are running `bun run codex-harness/index.ts` from inside `codex_jira_table_processor/`.

**`report_env/` not found**
Set up the Python virtual environment from the project root — see Prerequisites step 3 above.
