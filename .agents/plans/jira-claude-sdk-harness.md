# Feature: JIRA Table Analyzer — Claude Code SDK Harness

The following plan should be complete, but it's important that you validate documentation and
codebase patterns before you start implementing.

Pay special attention to import paths (`.ts` extensions required with `verbatimModuleSyntax`),
the `query()` async-generator pattern from `@anthropic-ai/claude-agent-sdk`, and the `.env`
variable names already defined in `.env.template`.

---

## Feature Description

Port `jira_table_analyze.py` to a TypeScript harness that uses the Claude Code SDK
(`@anthropic-ai/claude-agent-sdk`) to orchestrate a single Claude agent. The agent receives a
structured prompt containing all JIRA connection details and task instructions, then autonomously
executes the full workflow using its Bash and Write tools:

1. Connect to JIRA and fetch issues via JQL
2. Optionally enrich issues with remote links (VoxioTriageX report URL + log file names)
3. Process labels → determine Success / Failed status per ticket
4. Write `reports/jira_table.csv`, `reports/jira_status_report.csv`, `reports/jira_status_report.html`
5. Optionally send the HTML report via SMTP email

The Python script and its virtual environment (`report_env/`) stay untouched. The TypeScript
harness simply drives a Claude agent that executes the Python script inside that environment.

---

## User Story

As an on-call engineer  
I want to run a single command (`bun run claude-harness/index.ts`) that invokes a Claude agent  
So that JIRA issues are fetched, analyzed, and an HTML report is generated and optionally emailed — all orchestrated by the Claude Code SDK

---

## Problem Statement

The existing Python script works in isolation but has no SDK-based orchestration layer. We want to
wrap it in the Claude Code SDK so the agent can decide how to run the workflow, handle errors, and
stream progress back to the terminal — exactly as the `adversarial-dev` project does for code
generation.

---

## Solution Statement

Create a TypeScript harness inside a new top-level folder `claude_jira_table_processor/` at the
project root. This mirrors the structure of
`/Users/jyotirdiptadas/codebase/codex_research/adversarial-dev/claude-harness/` but simplified
to a single agent (no planner/generator/evaluator split — the JIRA workflow is linear, not
adversarial). The harness:

- Lives in `claude_jira_table_processor/` — isolated from the Python script and the Codex harness
- Reads `.env` from the project root (symlinked into the folder — see Task 1)
- Constructs a rich prompt describing the full task
- Calls `query()` from `@anthropic-ai/claude-agent-sdk` with `Bash` + `Write` tools
- The agent's `cwd` is set to the project root (`resolve("..")`) so it can find `jira_table_analyze.py`
- Streams tool calls and result messages to the terminal

---

## Feature Metadata

**Feature Type**: New Capability  
**Estimated Complexity**: Low  
**Primary Systems Affected**: New top-level `claude_jira_table_processor/` folder containing `claude-harness/`, `shared/`, `package.json`, `tsconfig.json`  
**Dependencies**: `@anthropic-ai/claude-agent-sdk` (npm), `bun` runtime, existing `report_env/` Python venv with `jira_table_analyze.py`

---

## CONTEXT REFERENCES

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `jira_table_analyze.py` (lines 903–993) — `main()` function: CLI args, `.env` loading, all env
  var names (`JIRA_URL`, `JIRA_API_TOKEN`, `JQL_QUERY`, `MAX_RESULTS`, `EMAIL_*`), date-range
  subject logic. This drives the exact prompt content.
- `jira_table_analyze.py` (lines 31–60) — `__init__` and `_connect()`: JIRA connection details
  the agent prompt must reference.
- `jira_table_analyze.py` (lines 819–900) — `run()` method: the 8-step workflow the agent must
  execute (fetch → enrich → csv → print → labels → status csv → html → email).
- `.env.template` — all env variable names and their defaults. The harness reads these at startup.
- `/Users/jyotirdiptadas/codebase/codex_research/adversarial-dev/claude-harness/index.ts` —
  **exact entry-point pattern to mirror**: arg parsing, config assembly, `runAnalyzer()` call,
  result logging, `process.exit()`.
- `/Users/jyotirdiptadas/codebase/codex_research/adversarial-dev/claude-harness/generator.ts`
  (full file) — **exact `query()` usage pattern** to mirror: `Options` type, async generator
  loop, `msg.type === "assistant"` block extraction, `msg.type === "result"` session capture,
  tool-use logging.
- `/Users/jyotirdiptadas/codebase/codex_research/adversarial-dev/shared/config.ts` — pattern for
  `CLAUDE_MODEL` constant and `DEFAULT_CONFIG`.
- `/Users/jyotirdiptadas/codebase/codex_research/adversarial-dev/shared/types.ts` — TypeScript
  interface style to mirror.
- `/Users/jyotirdiptadas/codebase/codex_research/adversarial-dev/package.json` — exact
  `package.json` shape: `"type": "module"`, `@types/bun` devDep, `typescript` peerDep.
- `/Users/jyotirdiptadas/codebase/codex_research/adversarial-dev/tsconfig.json` — copy verbatim,
  change `"exclude"` from `["workspace"]` to `["report_env", "workspace"]`.

### New Files to Create

```
jira-table-processor/
└── claude_jira_table_processor/     # ← ALL new files live inside this folder
    ├── .env -> ../.env              # symlink to project-root .env (see Task 1)
    ├── package.json                 # bun project manifest
    ├── tsconfig.json                # TypeScript config (copy from adversarial-dev, adjust exclude)
    ├── shared/
    │   ├── types.ts                 # AnalyzerConfig, AnalyzerResult interfaces
    │   ├── config.ts                # CLAUDE_MODEL, DEFAULT_CONFIG
    │   └── prompts.ts               # JIRA_ANALYZER_SYSTEM_PROMPT
    └── claude-harness/
        ├── index.ts                 # CLI entry point
        └── analyzer.ts              # Single-agent query() implementation
```

The root `README.md` is updated (not created inside the subfolder) to document this harness.

### Relevant Documentation — READ BEFORE IMPLEMENTING

- Claude Agent SDK `query()` reference: pattern is fully captured in
  `adversarial-dev/claude-harness/generator.ts` — no external URL needed; use that file as the
  authoritative reference.
- Bun `.env` loading: Bun auto-loads `.env` from the **current working directory** (the folder
  you `cd` into). Since the harness lives in `claude_jira_table_processor/`, a `.env` symlink
  pointing to `../.env` is required so Bun finds the credentials: `ln -s ../.env .env`.
- `@anthropic-ai/claude-agent-sdk` `Options` type fields used in this project:
  `cwd`, `systemPrompt`, `permissionMode`, `allowDangerouslySkipPermissions`,
  `tools`, `model`, `maxTurns`, `persistSession`.

---

## Patterns to Follow

### Import Style (verbatimModuleSyntax = true — `.ts` extensions REQUIRED)
```typescript
// CORRECT
import { query, type Options } from "@anthropic-ai/claude-agent-sdk";
import type { AnalyzerConfig } from "../shared/types.ts";
import { CLAUDE_MODEL } from "../shared/config.ts";

// WRONG — omitting .ts extension will cause a Bun resolution error
import { query } from "@anthropic-ai/claude-agent-sdk";   // OK (node_modules, no extension)
import type { AnalyzerConfig } from "../shared/types";    // WRONG
```

### query() Async Generator Pattern
Mirror exactly from `adversarial-dev/claude-harness/generator.ts`:
```typescript
for await (const msg of query({ prompt, options })) {
  if (msg.type === "assistant") {
    const message = msg as { message: { content: Array<{ type: string; text?: string; name?: string }> } };
    for (const block of message.message.content) {
      if (block.type === "text" && block.text) fullResponse += block.text;
      else if (block.type === "tool_use" && block.name) console.log(`  Tool: ${block.name}`);
    }
  } else if (msg.type === "result") {
    const result = msg as { session_id?: string };
    console.log(`Done (session: ${result.session_id?.slice(0, 8)}...)`);
  }
}
```

### Options Object Pattern
```typescript
const options: Options = {
  cwd: workDir,
  systemPrompt: JIRA_ANALYZER_SYSTEM_PROMPT,
  permissionMode: "bypassPermissions",
  allowDangerouslySkipPermissions: true,
  tools: ["Bash", "Write", "Read"],
  model: CLAUDE_MODEL,
  maxTurns: 50,
  persistSession: false,
};
```

### Console Logging (use plain `console.log` — no shared logger needed for single-agent)
```typescript
console.log("[HARNESS] Starting JIRA analysis...");
console.log("[AGENT]   Tool: Bash");
console.log("[HARNESS] Analysis complete");
```

### Env Loading (Bun auto-loads .env — just read `process.env`)
```typescript
const jiraUrl   = process.env["JIRA_URL"]        ?? "https://jira-sd.mc1.oracleiaas.com";
const apiToken  = process.env["JIRA_API_TOKEN"]  ?? "";
const jqlQuery  = process.env["JQL_QUERY"]       ?? "";
const maxResults = parseInt(process.env["MAX_RESULTS"] ?? "100", 10);
```

---

## IMPLEMENTATION PLAN

### Phase 1: Project Foundation
Set up the TypeScript/Bun project structure so `bun install` and `bun run` work.

**Tasks:**
- Create `package.json`
- Create `tsconfig.json`
- Create `shared/types.ts`
- Create `shared/config.ts`

### Phase 2: System Prompt
Write `shared/prompts.ts` with `JIRA_ANALYZER_SYSTEM_PROMPT`. This is the most important piece —
it tells the agent exactly what workflow to run, in what order, using which Python command.

### Phase 3: Agent Implementation
Create `claude-harness/analyzer.ts` with `runAnalyzer(config)` using the `query()` pattern.

### Phase 4: Entry Point
Create `claude-harness/index.ts` that parses `--detailed-report`, loads `.env`, builds the
`AnalyzerConfig`, calls `runAnalyzer()`, and exits with the right code.

### Phase 5: Documentation
Update the root `README.md` with a `## Claude SDK Harness` section that documents the
`claude_jira_table_processor/` folder, setup steps (including the `.env` symlink), and run commands.

---

## STEP-BY-STEP TASKS

### TASK 1 — CREATE `claude_jira_table_processor/` folder + `.env` symlink

- **IMPLEMENT**: Create the top-level folder and symlink `.env` from the project root
```bash
mkdir claude_jira_table_processor
cd claude_jira_table_processor
ln -s ../.env .env     # Bun loads .env from cwd — symlink keeps a single source of truth
```
- **GOTCHA**: All subsequent tasks create files **inside** `claude_jira_table_processor/`.
  Every `bun` command must be run from within this folder (`cd claude_jira_table_processor`).
- **VALIDATE**: `ls -la claude_jira_table_processor/.env` — should show a symlink to `../.env`

---

### TASK 2 — CREATE `claude_jira_table_processor/package.json`

- **IMPLEMENT**: Bun project manifest with `@anthropic-ai/claude-agent-sdk` dependency
- **PATTERN**: `adversarial-dev/package.json` — same shape exactly
- **CONTENT**:
```json
{
  "name": "jira-claude-harness",
  "module": "claude-harness/index.ts",
  "type": "module",
  "private": true,
  "devDependencies": {
    "@types/bun": "latest"
  },
  "peerDependencies": {
    "typescript": "^6.0.2"
  },
  "dependencies": {
    "@anthropic-ai/claude-agent-sdk": "^0.2.85"
  },
  "scripts": {
    "analyze": "bun run claude-harness/index.ts",
    "analyze:detailed": "bun run claude-harness/index.ts --detailed-report"
  }
}
```
- **VALIDATE**: `cd claude_jira_table_processor && bun install` — creates `node_modules/` and `bun.lockb`

---

### TASK 3 — CREATE `claude_jira_table_processor/tsconfig.json`

- **IMPLEMENT**: Copy `adversarial-dev/tsconfig.json` verbatim, change `exclude` array
- **GOTCHA**: `"exclude": ["node_modules", "workspace"]` — `report_env/` is in the parent dir,
  not inside `claude_jira_table_processor/`, so it does not need excluding here
- **VALIDATE**: `cd claude_jira_table_processor && bun run --bun tsc --noEmit` — zero type errors

---

### TASK 4 — CREATE `claude_jira_table_processor/shared/types.ts`

- **IMPLEMENT**: Two interfaces — `AnalyzerConfig` and `AnalyzerResult`
- **PATTERN**: Mirror interface style from `adversarial-dev/shared/types.ts`
```typescript
export interface AnalyzerConfig {
  jiraUrl: string;
  apiToken: string;
  jqlQuery: string;
  maxResults: number;
  detailedReport: boolean;
  workDir: string;
  emailConfig?: EmailConfig;
}

export interface EmailConfig {
  smtpServer: string;
  from: string;
  to: string;
  subject: string;
}

export interface AnalyzerResult {
  success: boolean;
  durationMs: number;
  outputFiles: string[];
  emailSent: boolean;
}
```
- **VALIDATE**: No standalone validation; validated when imported by other files

---

### TASK 5 — CREATE `claude_jira_table_processor/shared/config.ts`

- **IMPLEMENT**: Model constant and default config
- **PATTERN**: `adversarial-dev/shared/config.ts`
```typescript
import type { AnalyzerConfig } from "./types.ts";

export const CLAUDE_MODEL = "claude-sonnet-4-6";
export const CLAUDE_MAX_TURNS = 50;

export const DEFAULT_CONFIG: Pick<AnalyzerConfig, "maxResults" | "detailedReport"> = {
  maxResults: 100,
  detailedReport: false,
};
```
- **VALIDATE**: Imported cleanly by `analyzer.ts`

---

### TASK 6 — CREATE `claude_jira_table_processor/shared/prompts.ts`

- **IMPLEMENT**: `JIRA_ANALYZER_SYSTEM_PROMPT` — the most critical file
- **CONTENT REQUIREMENTS** (all must be in the prompt):
  1. Role: "You are a JIRA analysis agent. Your job is to execute a JIRA data analysis workflow."
  2. Environment: "The project root contains `jira_table_analyze.py` and a Python virtual
     environment at `report_env/`. Activate it with `source report_env/bin/activate`."
  3. Workflow instruction: "Run the analysis by executing:
     `source report_env/bin/activate && python3 jira_table_analyze.py [--detailed-report]`
     from the project root directory. The script reads all configuration from environment
     variables that are already set in the process."
  4. Output contract: "The script writes all output to the `reports/` directory:
     `reports/jira_table.csv`, `reports/jira_status_report.csv`,
     `reports/jira_status_report.html`. Report these files when done."
  5. Error handling: "If the script fails, capture stderr and report the error clearly.
     Do not retry silently."
  6. Completion signal: "When done, output a JSON summary:
     `{ \"success\": true/false, \"files\": [...], \"emailSent\": true/false }`"
- **GOTCHA**: The system prompt must NOT hardcode credentials — those are passed via env vars
  in the agent `options.cwd` working directory where `.env` is present.
- **VALIDATE**: Read the prompt text manually and confirm all 6 points are present

---

### TASK 7 — CREATE `claude_jira_table_processor/claude-harness/analyzer.ts`

- **IMPLEMENT**: `runAnalyzer(config: AnalyzerConfig): Promise<AnalyzerResult>`
- **PATTERN**: Mirror `adversarial-dev/claude-harness/generator.ts` exactly for `query()` usage
- **IMPORTS**:
```typescript
import { query, type Options } from "@anthropic-ai/claude-agent-sdk";
import { JIRA_ANALYZER_SYSTEM_PROMPT } from "../shared/prompts.ts";
import { CLAUDE_MODEL, CLAUDE_MAX_TURNS } from "../shared/config.ts";
import type { AnalyzerConfig, AnalyzerResult } from "../shared/types.ts";
```
- **PROMPT CONSTRUCTION**: Build the user prompt dynamically from `config`:
```typescript
const prompt = `
Run a complete JIRA analysis with the following parameters:
- JIRA URL: ${config.jiraUrl}
- JQL Query: ${config.jqlQuery}
- Max Results: ${config.maxResults}
- Detailed Report: ${config.detailedReport}
- Working Directory: ${config.workDir}
${config.emailConfig ? `- Email: send to ${config.emailConfig.to} via ${config.emailConfig.smtpServer}` : "- Email: not configured, skip"}

Execute the workflow now.
`.trim();
```
- **OPTIONS**:
```typescript
const options: Options = {
  cwd: config.workDir,
  systemPrompt: JIRA_ANALYZER_SYSTEM_PROMPT,
  permissionMode: "bypassPermissions",
  allowDangerouslySkipPermissions: true,
  tools: ["Bash", "Write", "Read"],
  model: CLAUDE_MODEL,
  maxTurns: CLAUDE_MAX_TURNS,
  persistSession: false,
};
```
- **RESULT PARSING**: After the loop, look for the JSON summary in `fullResponse` using the same
  multi-strategy extraction from `adversarial-dev/claude-harness/harness.ts` `parseContract()`:
  try last JSON code block → try `{...}` regex with `"success"` key → default to
  `{ success: false }`.
- **VALIDATE**: `cd claude_jira_table_processor && bun run --bun tsc --noEmit` — no type errors

---

### TASK 8 — CREATE `claude_jira_table_processor/claude-harness/index.ts`

- **IMPLEMENT**: CLI entry point — arg parsing, env loading, config assembly, orchestration
- **PATTERN**: Mirror `adversarial-dev/claude-harness/index.ts` exactly in structure
- **IMPORTS**:
```typescript
import { resolve } from "path";
import { runAnalyzer } from "./analyzer.ts";
import { DEFAULT_CONFIG } from "../shared/config.ts";
import type { AnalyzerConfig, EmailConfig } from "../shared/types.ts";
```
- **ARG PARSING**:
```typescript
const detailedReport = process.argv.includes("--detailed-report");
```
- **ENV LOADING** (Bun auto-loads `.env`):
```typescript
const jiraUrl  = process.env["JIRA_URL"]       ?? "https://jira-sd.mc1.oracleiaas.com";
const apiToken = process.env["JIRA_API_TOKEN"] ?? "";
const jqlQuery = process.env["JQL_QUERY"]      ?? "";
const maxResults = parseInt(process.env["MAX_RESULTS"] ?? "100", 10);
```
- **VALIDATION**: If `!apiToken`, print error message (mirror the Python `main()` error block at
  line 919–932 in `jira_table_analyze.py`) and `process.exit(1)`
- **DATE-RANGE SUBJECT LOGIC**: Mirror Python lines 953–958:
```typescript
let emailSubject = process.env["EMAIL_SUBJECT"] ?? "JIRA Status Report";
const createdMatch = jqlQuery.match(/created\s*>=\s*-(\d+)d/i);
if (createdMatch) {
  const daysBack = parseInt(createdMatch[1]!, 10);
  const today = new Date();
  const fromDate = new Date(today.getTime() - daysBack * 86400000);
  const fmt = (d: Date) => d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  emailSubject = `${emailSubject} from ${fmt(fromDate)} to ${fmt(today)}`;
}
```
- **EMAIL CONFIG ASSEMBLY**:
```typescript
const smtpServer = process.env["EMAIL_SMTP_SERVER"];
const emailFrom  = process.env["EMAIL_FROM"];
const emailTo    = process.env["EMAIL_TO"];
let emailConfig: EmailConfig | undefined;
if (smtpServer && emailFrom && emailTo) {
  emailConfig = { smtpServer, from: emailFrom, to: emailTo, subject: emailSubject };
}
```
- **CONFIG ASSEMBLY**:
```typescript
const config: AnalyzerConfig = {
  ...DEFAULT_CONFIG,
  jiraUrl,
  apiToken,
  jqlQuery,
  maxResults,
  detailedReport,
  workDir: resolve(".."),   // one level up = project root where jira_table_analyze.py lives
  emailConfig,
};
```
- **ORCHESTRATION** (mirror adversarial-dev index.ts try/catch structure):
```typescript
console.log("=".repeat(80));
console.log("[HARNESS] JIRA Claude SDK Harness");
console.log(`[HARNESS] JIRA: ${jiraUrl}`);
console.log(`[HARNESS] JQL:  ${jqlQuery}`);
console.log(`[HARNESS] Max:  ${maxResults} | Detailed: ${detailedReport}`);
console.log("=".repeat(80));

try {
  const result = await runAnalyzer(config);
  console.log(result.success ? "[HARNESS] Analysis complete!" : "[HARNESS] Analysis failed.");
  console.log(`[HARNESS] Duration: ${(result.durationMs / 1000).toFixed(1)}s`);
  process.exit(result.success ? 0 : 1);
} catch (error) {
  console.error(`[HARNESS] Fatal: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
}
```
- **VALIDATE**: `cd claude_jira_table_processor && bun run --bun tsc --noEmit` — zero errors

---

### TASK 9 — UPDATE root `README.md`

- **IMPLEMENT**: Add a `## Claude SDK Harness` section to the root `README.md`
- **GOTCHA**: The root `README.md` covers the Python script. **Append** the new section — do
  not overwrite existing content.
- **LOCATION NOTE**: All TypeScript files are inside `claude_jira_table_processor/`. The README
  section must clearly state this so users know where to `cd` before running commands.
- **SECTIONS TO INCLUDE**:

  **1. Overview** — one paragraph: what the harness does, that it uses `@anthropic-ai/claude-agent-sdk`,
  and that it drives the existing `jira_table_analyze.py` via a Claude agent.

  **2. Prerequisites**
  ```
  - Bun >= 1.0  (install: curl -fsSL https://bun.sh/install | bash)
  - claude CLI authenticated  (claude auth login)
  - Python venv with dependencies: report_env/ (already set up)
  ```

  **3. Installation**
  ```bash
  cd claude_jira_table_processor
  ln -s ../.env .env   # symlink project-root .env so Bun finds it
  bun install
  ```

  **4. Configuration** — table of all env vars read from `.env` (at project root):

  | Variable | Required | Default | Description |
  |---|---|---|---|
  | `JIRA_URL` | No | `https://jira-sd.mc1.oracleiaas.com` | JIRA instance URL |
  | `JIRA_API_TOKEN` | **Yes** | — | Personal API token |
  | `JQL_QUERY` | No | ExaInfra patching failures (last 3d) | JQL filter string |
  | `MAX_RESULTS` | No | `100` | Max issues to fetch |
  | `EMAIL_SMTP_SERVER` | No | — | SMTP hostname (port 25) |
  | `EMAIL_FROM` | No | — | Sender address |
  | `EMAIL_TO` | No | — | Comma-separated recipients |
  | `EMAIL_SUBJECT` | No | `JIRA Status Report` | Email subject prefix |

  **5. Usage** — all commands run from inside `claude_jira_table_processor/`:
  ```bash
  cd claude_jira_table_processor

  # Standard run
  bun run claude-harness/index.ts

  # With detailed report (fetches VoxioTriageX report URLs + log file names per ticket)
  bun run claude-harness/index.ts --detailed-report

  # Using npm scripts
  bun run analyze
  bun run analyze:detailed
  ```

  **6. Output Files** — what gets written to `reports/`:
  ```
  reports/
  ├── jira_table.csv             # All fetched issues (raw)
  ├── jira_status_report.csv     # Filtered: only Success/Failed tickets
  └── jira_status_report.html    # Styled HTML report with clickable JIRA links
  ```

  **7. Architecture** — short diagram:
  ```
  index.ts  ──(config)──▶  analyzer.ts  ──(query())──▶  Claude Agent
                                                              │
                                                    Bash tool (activates report_env,
                                                    runs jira_table_analyze.py)
                                                              │
                                                         reports/
  ```

  **8. How It Works** — 3-sentence explanation: harness reads `.env` → constructs a prompt →
  Claude agent uses its Bash tool to activate the Python venv and run `jira_table_analyze.py` →
  output files land in `reports/`.

- **VALIDATE**: Open `README.md` and confirm all 8 sections are present and render cleanly

---

## TESTING STRATEGY

### Manual End-to-End Test (primary validation)
There are no unit tests in the Python codebase; follow the same pattern — validate by running.

1. Ensure `.env` exists with valid `JIRA_API_TOKEN`
2. Run: `bun run claude-harness/index.ts`
3. Verify terminal shows agent tool calls (`[AGENT] Tool: Bash`, etc.)
4. Verify `reports/` directory is created with 3 files
5. Open `reports/jira_status_report.html` in a browser — confirm it renders correctly
6. Run: `bun run claude-harness/index.ts --detailed-report`
7. Verify Report Link and Log Files columns appear in the HTML

### Edge Cases to Verify
- Missing `JIRA_API_TOKEN` → harness exits with error before calling agent (not agent failure)
- No issues matching JQL → agent reports "No matching issues" without crashing
- Email env vars not set → workflow completes without emailing, no error

---

## VALIDATION COMMANDS

All commands run from inside `claude_jira_table_processor/`:

### Level 1: Folder + Symlink
```bash
cd /Users/jyotirdiptadas/codebase/jira-table-processor/claude_jira_table_processor
ls -la .env
```
Expected: `.env -> ../.env` symlink present

### Level 2: Dependency Install
```bash
cd /Users/jyotirdiptadas/codebase/jira-table-processor/claude_jira_table_processor
bun install
```
Expected: `node_modules/@anthropic-ai/claude-agent-sdk` present, `bun.lockb` created

### Level 3: Type Check
```bash
cd /Users/jyotirdiptadas/codebase/jira-table-processor/claude_jira_table_processor
bun run --bun tsc --noEmit
```
Expected: zero errors, zero warnings

### Level 4: Auth Check
```bash
claude auth status
```
Expected: logged in (run `claude auth login` if not)

### Level 5: Dry-Run (no JIRA — expect auth error from agent, not harness crash)
```bash
cd /Users/jyotirdiptadas/codebase/jira-table-processor/claude_jira_table_processor
JIRA_API_TOKEN=fake JQL_QUERY="project = TEST" bun run claude-harness/index.ts
```
Expected: harness starts, agent runs, agent reports JIRA connection failure gracefully

### Level 6: Full Run (requires real `.env`)
```bash
cd /Users/jyotirdiptadas/codebase/jira-table-processor/claude_jira_table_processor
bun run claude-harness/index.ts
```
Expected: `../reports/jira_status_report.html` created (in the project root `reports/` folder)

### Level 7: Detailed Report Flag
```bash
cd /Users/jyotirdiptadas/codebase/jira-table-processor/claude_jira_table_processor
bun run claude-harness/index.ts --detailed-report
```
Expected: `../reports/jira_status_report.html` includes Report and Log Files columns

---

## ACCEPTANCE CRITERIA

- [ ] `bun install` completes without errors
- [ ] `bun run --bun tsc --noEmit` passes with zero errors
- [ ] Missing `JIRA_API_TOKEN` exits with a clear error message before invoking the agent
- [ ] Running the harness with a valid `.env` produces all 3 report files in `reports/`
- [ ] `--detailed-report` flag is passed through correctly to the Python script
- [ ] Email is sent when all 4 `EMAIL_*` env vars are present
- [ ] Agent tool calls are visible in terminal output during execution
- [ ] `process.exit(0)` on success, `process.exit(1)` on failure
- [ ] No TypeScript `any` usage without cast (strict mode on)
- [ ] Existing `jira_table_analyze.py` and `report_env/` are not modified
- [ ] `README.md` updated with Claude SDK harness section (all 8 sections present)

---

## COMPLETION CHECKLIST

- [ ] `package.json` created and `bun install` succeeds
- [ ] `tsconfig.json` created with `report_env` excluded
- [ ] `shared/types.ts` — `AnalyzerConfig`, `EmailConfig`, `AnalyzerResult`
- [ ] `shared/config.ts` — `CLAUDE_MODEL`, `CLAUDE_MAX_TURNS`, `DEFAULT_CONFIG`
- [ ] `shared/prompts.ts` — `JIRA_ANALYZER_SYSTEM_PROMPT` with all 6 required points
- [ ] `claude-harness/analyzer.ts` — `runAnalyzer()` with `query()` loop and result parsing
- [ ] `claude-harness/index.ts` — arg parsing, env loading, date-subject logic, orchestration
- [ ] `README.md` — updated with Claude SDK harness section (8 sections, env var table, arch diagram)
- [ ] All type checks pass
- [ ] End-to-end run produces correct output files

---

## NOTES

### Why Single Agent (not multi-agent like adversarial-dev)
The JIRA workflow is a **linear pipeline** — there is nothing adversarial or iterative about it.
Breaking it into multiple agents (fetcher → processor → reporter) would add complexity with no
benefit. The existing Python script already handles all three stages; the agent's job is simply
to execute it correctly.

### Why the Agent Runs Python (not re-implement in TypeScript)
The Python `jira` library, pandas, and the HTML generation logic are already tested and working.
Re-implementing them in TypeScript would be significant work for no gain. The Claude agent's
`Bash` tool is the right bridge here — it activates the venv and runs the script.

### workDir
`workDir` is set to `resolve("..")` — one level up from `claude_jira_table_processor/` — which
resolves to the project root where `jira_table_analyze.py` and `report_env/` live. The `cwd`
option on the agent ensures all Bash commands run from there, so
`python3 jira_table_analyze.py` and `source report_env/bin/activate` resolve correctly.

### Bun .env Auto-loading
Bun loads `.env` from the **current working directory**. Since we run commands from inside
`claude_jira_table_processor/`, a `.env` symlink (`ln -s ../.env .env`) is created in that
folder so Bun finds the credentials without duplicating the file.

### .gitignore
Add to existing `.gitignore` at project root (do NOT create a new one):
```
claude_jira_table_processor/node_modules/
claude_jira_table_processor/bun.lockb
claude_jira_table_processor/.env
```

---

**Confidence Score: 9/10**

The SDK pattern is fully captured from adversarial-dev (no guessing). All env vars are documented
in `.env.template`. The Python script is already working — the agent only needs to call it.
The only uncertainty is the exact `query()` message type shapes at runtime, which are handled
by the same defensive casting pattern used in adversarial-dev.
