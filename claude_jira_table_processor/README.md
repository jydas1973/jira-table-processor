# JIRA Claude SDK Harness

A TypeScript harness that uses the **Anthropic Claude Agent SDK** to orchestrate a Claude agent
that fetches JIRA issues, analyzes labels, and generates HTML/CSV reports — all driven by a
single command.

---

## Quick Start — Generate a Report

```bash
# From inside this folder:
cd claude_jira_table_processor

# Install dependencies (first time only)
bun install

# Run standard report
bun run analyze

# Run with detailed report (adds VoxioTriageX report URLs + log file columns)
bun run analyze:detailed
```

Reports are written to `claude_jira_table_processor/reports/`:

```
reports/
├── jira_table.csv             # All fetched issues (raw)
├── jira_status_report.csv     # Filtered: only Success/Failed tickets
└── jira_status_report.html    # Styled HTML with clickable JIRA links
```

---

## Prerequisites

| Requirement | Install |
|---|---|
| Bun >= 1.0 | `curl -fsSL https://bun.sh/install \| bash` |
| Claude CLI authenticated | `claude auth login` |
| Python venv (`../report_env/`) | Already set up — see root README |

---

## Environment Variables

All variables are read from `.env` in this folder (symlinked to the project root `.env`).

| Variable | Required | Default | Description |
|---|---|---|---|
| `JIRA_URL` | No | `https://jira-sd.mc1.oracleiaas.com` | JIRA instance URL |
| `JIRA_API_TOKEN` | **Yes** | — | Personal API token |
| `JQL_QUERY` | No | ExaInfra patching failures (last 3d) | JQL filter string |
| `MAX_RESULTS` | No | `100` | Max issues to fetch |
| `EMAIL_SMTP_SERVER` | No | — | SMTP hostname (port 25, no auth) |
| `EMAIL_FROM` | No | — | Sender email address |
| `EMAIL_TO` | No | — | Comma-separated recipients |
| `EMAIL_SUBJECT` | No | `JIRA Status Report` | Subject prefix (date range appended automatically) |

The harness exits immediately with an error if `JIRA_API_TOKEN` is not set.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│  index.ts                                                           │
│  • Loads .env (Bun auto-loads from cwd)                             │
│  • Parses --detailed-report flag                                    │
│  • Validates JIRA_API_TOKEN                                         │
│  • Assembles AnalyzerConfig (jiraUrl, jqlQuery, emailConfig, …)     │
│  • Calls runAnalyzer(config)                                        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ config
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  analyzer.ts                                                        │
│  • Builds user prompt from config fields                            │
│  • Calls query() from @anthropic-ai/claude-agent-sdk               │
│  • Streams tool calls to terminal ([AGENT] Tool: Bash)              │
│  • Parses JSON completion summary from agent response               │
│  • Returns AnalyzerResult { success, durationMs, outputFiles, … }   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ query()
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Claude Agent (claude-sonnet-4-6)                                   │
│  System prompt: JIRA_ANALYZER_SYSTEM_PROMPT                         │
│  cwd: claude_jira_table_processor/                                  │
│  Tools: Bash, Write, Read                                           │
│                                                                     │
│  Agent executes:                                                    │
│    source ../report_env/bin/activate &&                             │
│    python3 ../jira_table_analyze.py [--detailed-report]             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ writes
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  claude_jira_table_processor/reports/                               │
│  ├── jira_table.csv                                                 │
│  ├── jira_status_report.csv                                         │
│  └── jira_status_report.html                                        │
└─────────────────────────────────────────────────────────────────────┘
```

### Step-by-step flow

1. **Harness starts** — `index.ts` reads `.env`, validates the API token, and assembles config.
2. **Prompt construction** — `analyzer.ts` builds a user prompt with JIRA URL, JQL, max results,
   and email settings, then calls `query()` from the Claude Agent SDK.
3. **Agent executes** — Claude activates the Python venv (`../report_env/`) and runs
   `../jira_table_analyze.py`, which connects to JIRA, fetches issues matching the JQL filter,
   processes labels to determine Success/Failed status, and writes three output files to `reports/`.
4. **Streaming** — each Bash tool call is printed to the terminal as `[AGENT] Tool: Bash`.
5. **Completion** — the agent emits a JSON summary; the harness parses it and exits `0` on
   success or `1` on failure.

---

## Project Structure

```
claude_jira_table_processor/
├── .env                     → symlink to ../.env (project root credentials)
├── package.json             bun project manifest
├── tsconfig.json            TypeScript config (strict, verbatimModuleSyntax)
├── README.md                this file
├── reports/                 generated reports (gitignored)
│   ├── jira_table.csv
│   ├── jira_status_report.csv
│   └── jira_status_report.html
├── shared/
│   ├── types.ts             AnalyzerConfig, EmailConfig, AnalyzerResult
│   ├── config.ts            CLAUDE_MODEL, CLAUDE_MAX_TURNS, DEFAULT_CONFIG
│   └── prompts.ts           JIRA_ANALYZER_SYSTEM_PROMPT
└── claude-harness/
    ├── index.ts             CLI entry point
    └── analyzer.ts          query() agent loop + result parsing
```

---

## Troubleshooting

**`JIRA_API_TOKEN is not set`** — Copy `.env.template` from the project root to `.env` and fill in your token.

**`ModuleNotFoundError`** — The Python venv may be missing packages. Run `pip install -r ../requirements.txt` inside `../report_env/`.

**Agent reports JIRA auth failure** — Your `JIRA_API_TOKEN` is invalid or expired. Regenerate it in your Atlassian account settings.

**`bun: command not found`** — Install Bun: `curl -fsSL https://bun.sh/install | bash`, then restart your terminal.
