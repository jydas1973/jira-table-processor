# Feature: JIRA Table Analyzer — Codex SDK Harness

The following plan should be complete, but it's important that you validate documentation and
codebase patterns before you start implementing.

Pay special attention to:
- The `runStreamed()` event loop and the **mandatory `break` on `turn.completed`** (skipping this
  causes a 90-second timeout hang)
- System prompts must be **prepended into the user prompt string** — there is no separate
  `systemPrompt` option in the Codex SDK
- `.ts` extensions are required on all local imports (`verbatimModuleSyntax: true`)

---

## Feature Description

Port `jira_table_analyze.py` to a TypeScript harness that uses the Codex SDK
(`@openai/codex-sdk`) to orchestrate a single Codex agent. The agent receives a structured
prompt containing all JIRA connection details and task instructions, then autonomously executes
the full workflow using its implicit sandbox tools (file system + shell access via
`sandboxMode: "danger-full-access"`):

1. Connect to JIRA and fetch issues via JQL
2. Optionally enrich issues with remote links (VoxioTriageX report URL + log file names)
3. Process labels → determine Success / Failed status per ticket
4. Write `reports/jira_table.csv`, `reports/jira_status_report.csv`, `reports/jira_status_report.html`
5. Optionally send the HTML report via SMTP email

The Python script and its virtual environment (`report_env/`) stay untouched. The TypeScript
harness drives a Codex agent that executes the Python script inside that environment.

---

## User Story

As an on-call engineer  
I want to run a single command (`bun run codex-harness/index.ts`) that invokes a Codex agent  
So that JIRA issues are fetched, analyzed, and an HTML report is generated and optionally emailed — all orchestrated by the Codex SDK

---

## Problem Statement

The existing Python script works in isolation but has no SDK-based orchestration layer. This
harness wraps it in the Codex SDK so the agent can decide how to run the workflow, stream
command execution progress to the terminal, and report back on completion.

---

## Solution Statement

Create a TypeScript harness inside a new top-level folder `codex_jira_table_processor/` at the
project root, mirroring the structure of
`/Users/jyotirdiptadas/codebase/codex_research/adversarial-dev/codex-harness/` but simplified
to a single agent (no planner/generator/evaluator split — the JIRA workflow is linear). The
harness:

- Lives in `codex_jira_table_processor/` — isolated from the Python script and the Claude harness
- Reads `.env` from the project root (symlinked into the folder — see Task 1)
- Prepends `JIRA_ANALYZER_SYSTEM_PROMPT` into the user prompt string (Codex has no separate
  `systemPrompt` option)
- The agent's `workingDirectory` is set to the project root (`resolve("..")`) so it can find
  `jira_table_analyze.py` and `report_env/`
- Calls `thread.runStreamed()` for real-time visibility of shell commands the agent executes
- Breaks the event loop on `turn.completed` (critical — prevents 90s timeout)
- Reports `turn.finalResponse` as the agent's summary

---

## Feature Metadata

**Feature Type**: New Capability  
**Estimated Complexity**: Low  
**Primary Systems Affected**: New top-level `codex_jira_table_processor/` folder containing `codex-harness/`, `shared/`, `package.json`, `tsconfig.json`  
**Dependencies**: `@openai/codex-sdk` (npm), `bun` runtime, existing `report_env/` Python venv with `jira_table_analyze.py`

---

## CONTEXT REFERENCES

### Relevant Codebase Files — MUST READ BEFORE IMPLEMENTING

- `jira_table_analyze.py` (lines 903–993) — `main()`: all env var names (`JIRA_URL`,
  `JIRA_API_TOKEN`, `JQL_QUERY`, `MAX_RESULTS`, `EMAIL_*`), `--detailed-report` flag,
  date-range subject logic.
- `jira_table_analyze.py` (lines 819–900) — `run()`: the 8-step workflow the agent must execute.
- `.env.template` — all env variable names and their defaults.
- `/Users/jyotirdiptadas/codebase/codex_research/adversarial-dev/codex-harness/generator.ts`
  (full file) — **authoritative `runStreamed()` pattern**: event loop, `item.completed`,
  `turn.completed` with mandatory `break`, `error` handling, token usage logging.
- `/Users/jyotirdiptadas/codebase/codex_research/adversarial-dev/codex-harness/planner.ts`
  (full file) — **authoritative `thread.run()` pattern**: system prompt prepending, `new Codex()`,
  `startThread()` options, `turn.finalResponse`.
- `/Users/jyotirdiptadas/codebase/codex_research/adversarial-dev/codex-harness/index.ts`
  (full file) — entry-point structure to mirror.
- `/Users/jyotirdiptadas/codebase/codex_research/adversarial-dev/shared/config.ts` —
  `CODEX_MODEL` and `CODEX_NETWORK_ACCESS` constants pattern.
- `.agents/plans/jira-claude-sdk-harness.md` — the parallel Claude SDK plan for this same
  feature. Use it as a structural reference; the Codex plan diverges in SDK mechanics only.

### New Files to Create

```
jira-table-processor/
└── codex_jira_table_processor/      # ← ALL new files live inside this folder
    ├── .env -> ../.env              # symlink to project-root .env (see Task 1)
    ├── package.json                 # bun project manifest with @openai/codex-sdk
    ├── tsconfig.json                # TypeScript config
    ├── shared/
    │   ├── types.ts                 # AnalyzerConfig, EmailConfig, AnalyzerResult
    │   ├── config.ts                # CODEX_MODEL, CODEX_NETWORK_ACCESS, DEFAULT_CONFIG
    │   └── prompts.ts               # JIRA_ANALYZER_SYSTEM_PROMPT
    └── codex-harness/
        ├── index.ts                 # CLI entry point
        └── analyzer.ts              # Single-agent runStreamed() implementation
```

The root `README.md` is updated (not a new file inside the subfolder) to document this harness.

> **Note**: `shared/` here is **independent** from `claude_jira_table_processor/shared/` — each
> harness folder is fully self-contained with its own `node_modules/`, `package.json`, and
> `shared/` types. No cross-folder imports.

### Relevant Documentation — READ BEFORE IMPLEMENTING

- All Codex SDK patterns are fully captured in the `adversarial-dev/codex-harness/` files above.
  No external URLs needed.
- Auth: run `codex auth login` once before first use (analogous to `claude auth login`).
- Bun `.env` auto-loading: Bun loads `.env` from the **current working directory**. Since we
  run commands from inside `codex_jira_table_processor/`, a `.env` symlink pointing to `../.env`
  is required: `ln -s ../.env .env`.

---

## Patterns to Follow

### Import Style (verbatimModuleSyntax = true — `.ts` extensions REQUIRED on local imports)
```typescript
// CORRECT
import { Codex } from "@openai/codex-sdk";              // node_modules — no extension
import type { AnalyzerConfig } from "../shared/types.ts"; // local — .ts required
import { CODEX_MODEL, CODEX_NETWORK_ACCESS } from "../shared/config.ts";

// WRONG
import type { AnalyzerConfig } from "../shared/types"; // missing .ts — Bun resolution error
```

### Client + Thread Creation (exact pattern from codex-harness/planner.ts and generator.ts)
```typescript
const codex = new Codex();   // no constructor arguments
const thread = codex.startThread({
  workingDirectory: workDir,
  sandboxMode: "danger-full-access",
  networkAccessEnabled: CODEX_NETWORK_ACCESS,  // true
  approvalPolicy: "never",
  model: CODEX_MODEL,                           // "gpt-5.4"
});
```

### System Prompt Delivery (NO separate field — prepend into prompt string)
```typescript
// CORRECT — Codex pattern
const fullPrompt = `${JIRA_ANALYZER_SYSTEM_PROMPT}\n\n---\n\n${taskPrompt}`;
await thread.runStreamed(fullPrompt);

// WRONG — Claude SDK pattern, does NOT work with Codex
const options = { systemPrompt: JIRA_ANALYZER_SYSTEM_PROMPT };  // no such option
```

### Streaming Event Loop (exact pattern from codex-harness/generator.ts)
```typescript
const { events } = await thread.runStreamed(fullPrompt);

let fullResponse = "";

for await (const event of events) {
  if (event.type === "item.completed") {
    const item = event.item as Record<string, unknown>;
    if (item.type === "agent_message" && typeof item.text === "string") {
      fullResponse += item.text;
    } else if (item.type === "command_execution" && typeof item.command === "string") {
      console.log(`[AGENT]   Command: ${item.command}`);
    }
  } else if (event.type === "turn.completed") {
    const turnEvent = event as { usage?: { input_tokens?: number; output_tokens?: number } };
    const usage = turnEvent.usage;
    if (usage) {
      console.log(`[AGENT]   Tokens: ${usage.input_tokens ?? 0} in / ${usage.output_tokens ?? 0} out`);
    }
    console.log("[AGENT]   Turn complete");
    break; // CRITICAL: must break here — skipping causes a 90-second hang
  } else if (event.type === "error") {
    const errorEvent = event as { message?: string };
    console.error(`[AGENT]   Stream error: ${errorEvent.message ?? "unknown"}`);
  }
}
```

### Synchronous Turn (for short operations like auth validation — pattern from planner.ts)
```typescript
const turn = await thread.run(prompt);
const response = turn.finalResponse ?? "";  // string | undefined — always guard with ??
```

### No Tools List (tools are implicit via sandboxMode)
```typescript
// CORRECT — Codex grants all tools via sandboxMode
codex.startThread({ sandboxMode: "danger-full-access", ... });

// WRONG — there is no tools array in Codex startThread options
codex.startThread({ tools: ["Bash", "Write"], ... });  // does not exist
```

### Env Loading (Bun auto-loads .env)
```typescript
const jiraUrl    = process.env["JIRA_URL"]        ?? "https://jira-sd.mc1.oracleiaas.com";
const apiToken   = process.env["JIRA_API_TOKEN"]  ?? "";
const jqlQuery   = process.env["JQL_QUERY"]       ?? "";
const maxResults = parseInt(process.env["MAX_RESULTS"] ?? "100", 10);
```

---

## IMPLEMENTATION PLAN

### Phase 1: Project Foundation
Update `package.json` to add `@openai/codex-sdk`. Update or create `shared/config.ts` and
`shared/types.ts` with Codex constants and types.

### Phase 2: System Prompt
Create `codex_jira_table_processor/shared/prompts.ts` with `JIRA_ANALYZER_SYSTEM_PROMPT`.

### Phase 3: Agent Implementation
Create `codex_jira_table_processor/codex-harness/analyzer.ts` with `runAnalyzer()` using
`thread.runStreamed()`.

### Phase 4: Entry Point
Create `codex_jira_table_processor/codex-harness/index.ts` — args, env, config, orchestration.

### Phase 5: Documentation
Update the root `README.md` with a `## Codex SDK Harness` section documenting the
`codex_jira_table_processor/` folder, setup steps (including the `.env` symlink), and run commands.

---

## STEP-BY-STEP TASKS

### TASK 1 — CREATE `codex_jira_table_processor/` folder + `.env` symlink

- **IMPLEMENT**: Create the top-level folder and symlink `.env` from the project root
```bash
mkdir codex_jira_table_processor
cd codex_jira_table_processor
ln -s ../.env .env     # Bun loads .env from cwd — symlink keeps a single source of truth
```
- **GOTCHA**: All subsequent tasks create files **inside** `codex_jira_table_processor/`.
  Every `bun` command must be run from within this folder (`cd codex_jira_table_processor`).
- **VALIDATE**: `ls -la codex_jira_table_processor/.env` — should show a symlink to `../.env`

---

### TASK 2 — CREATE `codex_jira_table_processor/package.json`

- **IMPLEMENT**: Bun project manifest with `@openai/codex-sdk` dependency
- **PATTERN**: `adversarial-dev/package.json` — same shape, Codex SDK only (self-contained)
```json
{
  "name": "jira-codex-harness",
  "module": "codex-harness/index.ts",
  "type": "module",
  "private": true,
  "devDependencies": {
    "@types/bun": "latest"
  },
  "peerDependencies": {
    "typescript": "^6.0.2"
  },
  "dependencies": {
    "@openai/codex-sdk": "^0.117.0"
  },
  "scripts": {
    "analyze": "bun run codex-harness/index.ts",
    "analyze:detailed": "bun run codex-harness/index.ts --detailed-report"
  }
}
```
- **VALIDATE**: `cd codex_jira_table_processor && bun install` — `node_modules/@openai/codex-sdk` present

---

### TASK 3 — CREATE `codex_jira_table_processor/tsconfig.json`

- **IMPLEMENT**: Copy `adversarial-dev/tsconfig.json` verbatim, change `exclude` array
- **GOTCHA**: `"exclude": ["node_modules", "workspace"]` — `report_env/` is in the parent dir,
  not inside `codex_jira_table_processor/`, so it does not need excluding here
- **VALIDATE**: `cd codex_jira_table_processor && bun run --bun tsc --noEmit` — zero type errors

---

### TASK 4 — CREATE `codex_jira_table_processor/shared/config.ts`

- **IMPLEMENT**: `CODEX_MODEL`, `CODEX_NETWORK_ACCESS`, and `DEFAULT_CONFIG` — self-contained,
  no dependency on the Claude harness folder
```typescript
import type { AnalyzerConfig } from "./types.ts";

export const CODEX_MODEL = "gpt-5.4";
export const CODEX_NETWORK_ACCESS = true;

export const DEFAULT_CONFIG: Pick<AnalyzerConfig, "maxResults" | "detailedReport"> = {
  maxResults: 100,
  detailedReport: false,
};
```
- **VALIDATE**: Imported cleanly by `codex-harness/analyzer.ts`

---

### TASK 5 — CREATE `codex_jira_table_processor/shared/types.ts`

- **IMPLEMENT**: `AnalyzerConfig`, `EmailConfig`, `AnalyzerResult` — identical shape to Claude
  harness types (SDK-agnostic), but defined independently in this folder:
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
- **VALIDATE**: No type errors on import

---

### TASK 6 — CREATE `codex_jira_table_processor/shared/prompts.ts`

- **IMPLEMENT**: `JIRA_ANALYZER_SYSTEM_PROMPT` — identical content to Claude harness prompt
  (SDK-agnostic), defined independently in this folder
- **CONTENT REQUIREMENTS** (same as Claude plan — the prompt is SDK-agnostic):
  1. Role: JIRA analysis agent
  2. Environment: project root contains `jira_table_analyze.py`, venv at `report_env/`
  3. Workflow: `source report_env/bin/activate && python3 jira_table_analyze.py [--detailed-report]`
  4. Output contract: files written to `reports/` directory
  5. Error handling: capture stderr, report clearly, do not retry silently
  6. Completion signal: output JSON `{ "success": true/false, "files": [...], "emailSent": true/false }`
- **VALIDATE**: Exported and importable without errors

---

### TASK 7 — CREATE `codex_jira_table_processor/codex-harness/analyzer.ts`

- **IMPLEMENT**: `runAnalyzer(config: AnalyzerConfig): Promise<AnalyzerResult>`
- **PATTERN**: Mirror `adversarial-dev/codex-harness/generator.ts` for `runStreamed()` and
  `adversarial-dev/codex-harness/planner.ts` for `startThread()` options
- **IMPORTS**:
```typescript
import { Codex } from "@openai/codex-sdk";
import { JIRA_ANALYZER_SYSTEM_PROMPT } from "../shared/prompts.ts";
import { CODEX_MODEL, CODEX_NETWORK_ACCESS } from "../shared/config.ts";
import type { AnalyzerConfig, AnalyzerResult } from "../shared/types.ts";
```
- **PROMPT CONSTRUCTION**:
```typescript
const taskPrompt = `
Run a complete JIRA analysis with the following parameters:
- JIRA URL: ${config.jiraUrl}
- JQL Query: ${config.jqlQuery}
- Max Results: ${config.maxResults}
- Detailed Report: ${config.detailedReport}
- Working Directory: ${config.workDir}
${config.emailConfig
  ? `- Email: send to ${config.emailConfig.to} via ${config.emailConfig.smtpServer}`
  : "- Email: not configured, skip"}

Execute the workflow now.
`.trim();

const fullPrompt = `${JIRA_ANALYZER_SYSTEM_PROMPT}\n\n---\n\n${taskPrompt}`;
```
- **THREAD + STREAMING**:
```typescript
const codex = new Codex();
const thread = codex.startThread({
  workingDirectory: config.workDir,
  sandboxMode: "danger-full-access",
  networkAccessEnabled: CODEX_NETWORK_ACCESS,
  approvalPolicy: "never",
  model: CODEX_MODEL,
});

const { events } = await thread.runStreamed(fullPrompt);
let fullResponse = "";

for await (const event of events) {
  if (event.type === "item.completed") {
    const item = event.item as Record<string, unknown>;
    if (item.type === "agent_message" && typeof item.text === "string") {
      fullResponse += item.text;
    } else if (item.type === "command_execution" && typeof item.command === "string") {
      console.log(`[AGENT]   Command: ${item.command}`);
    }
  } else if (event.type === "turn.completed") {
    const turnEvent = event as { usage?: { input_tokens?: number; output_tokens?: number } };
    const u = turnEvent.usage;
    if (u) console.log(`[AGENT]   Tokens: ${u.input_tokens ?? 0} in / ${u.output_tokens ?? 0} out`);
    break; // CRITICAL — must break to avoid 90s timeout
  } else if (event.type === "error") {
    const e = event as { message?: string };
    console.error(`[AGENT]   Error: ${e.message ?? "unknown"}`);
  }
}
```
- **RESULT PARSING**: Same 3-strategy JSON extraction as `adversarial-dev/codex-harness/evaluator.ts`:
  1. Last JSON code block in `fullResponse`
  2. `{...}` regex containing `"success"`
  3. Raw `fullResponse`
  Fall back to `{ success: false, durationMs, outputFiles: [], emailSent: false }` on parse failure.
- **VALIDATE**: `cd codex_jira_table_processor && bun run --bun tsc --noEmit` — zero type errors

---

### TASK 8 — CREATE `codex_jira_table_processor/codex-harness/index.ts`

- **IMPLEMENT**: CLI entry point — arg parsing, env loading, config assembly, orchestration
- **PATTERN**: Mirror `adversarial-dev/codex-harness/index.ts` structure exactly, substituting
  the JIRA-specific config
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
- **ENV + VALIDATION** (same as Claude harness index.ts):
```typescript
const jiraUrl    = process.env["JIRA_URL"]        ?? "https://jira-sd.mc1.oracleiaas.com";
const apiToken   = process.env["JIRA_API_TOKEN"]  ?? "";
const jqlQuery   = process.env["JQL_QUERY"]       ?? "";
const maxResults = parseInt(process.env["MAX_RESULTS"] ?? "100", 10);

if (!apiToken) {
  console.error("ERROR: JIRA_API_TOKEN is not set. Please configure .env.");
  process.exit(1);
}
```
- **DATE-RANGE SUBJECT LOGIC** (mirror `jira_table_analyze.py` lines 953–958):
```typescript
let emailSubject = process.env["EMAIL_SUBJECT"] ?? "JIRA Status Report";
const createdMatch = jqlQuery.match(/created\s*>=\s*-(\d+)d/i);
if (createdMatch) {
  const daysBack = parseInt(createdMatch[1]!, 10);
  const today = new Date();
  const fromDate = new Date(today.getTime() - daysBack * 86400000);
  const fmt = (d: Date) =>
    d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  emailSubject = `${emailSubject} from ${fmt(fromDate)} to ${fmt(today)}`;
}
```
- **EMAIL + CONFIG ASSEMBLY** (identical to Claude harness):
```typescript
const smtpServer = process.env["EMAIL_SMTP_SERVER"];
const emailFrom  = process.env["EMAIL_FROM"];
const emailTo    = process.env["EMAIL_TO"];
const emailConfig: EmailConfig | undefined =
  smtpServer && emailFrom && emailTo
    ? { smtpServer, from: emailFrom, to: emailTo, subject: emailSubject }
    : undefined;

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
- **ORCHESTRATION**:
```typescript
console.log("=".repeat(80));
console.log("[HARNESS] JIRA Codex SDK Harness");
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
- **VALIDATE**: `cd codex_jira_table_processor && bun run --bun tsc --noEmit` — zero errors

---

### TASK 9 — UPDATE root `README.md`

- **IMPLEMENT**: Add a `## Codex SDK Harness` section to the root `README.md`
- **GOTCHA**: `README.md` already exists. **Append** the new section — do not overwrite.
- **LOCATION NOTE**: All TypeScript files are inside `codex_jira_table_processor/`. The README
  section must clearly state this so users know where to `cd` before running commands.
- **STATUS**: A Codex SDK Harness section has already been written to `README.md`. Verify it
  is present and accurate — update only if content has drifted from the implementation.
- **SECTIONS REQUIRED**:

  **1. Overview** — what the Codex harness does; lives in `codex_jira_table_processor/`; uses
  `@openai/codex-sdk`; drives `jira_table_analyze.py` via a Codex agent.

  **2. Prerequisites** — Bun >= 1.0 (install command), OpenAI API Key, Python venv.

  **3. Authentication** — two options documented:
  - **Option 1 (recommended)**: Add `OPENAI_API_KEY=sk-...` to root `.env`
  - **Option 2**: `codex auth login` — OAuth flow, caches token at `~/.codex/`

  **4. Installation**
  ```bash
  cd codex_jira_table_processor
  ln -s ../.env .env   # symlink project-root .env
  bun install
  ```

  **5. Configuration** — env var table including `OPENAI_API_KEY`, plus all JIRA and email vars

  **6. Usage** — all commands from inside `codex_jira_table_processor/`:
  ```bash
  cd codex_jira_table_processor
  bun run codex-harness/index.ts
  bun run codex-harness/index.ts --detailed-report
  bun run analyze
  bun run analyze:detailed
  ```

  **7. What Happens End-to-End** — `.env` (symlinked) read → `AnalyzerConfig` built with
  `workDir: resolve("..")` → `new Codex()` + `startThread(workingDirectory: projectRoot)` →
  `runStreamed()` → streaming `[AGENT] Command:` lines → `break` on `turn.completed` → `reports/`

  **8. Output Files** — `reports/jira_table.csv`, `reports/jira_status_report.csv`,
  `reports/jira_status_report.html` (all in the project root `reports/` folder, not inside
  `codex_jira_table_processor/`)

  **9. Architecture diagram** — ASCII diagram showing `index.ts → analyzer.ts →
  runStreamed() → Codex Agent (workDir=..) → sandbox shell → ../reports/`

  **10. Key Difference from Claude SDK Harness** — no `systemPrompt` option (prepend into
  prompt), no explicit tool list (`sandboxMode` grants all), `runStreamed()` with mandatory
  `break` on `turn.completed` (90s hang if omitted)

  **11. Troubleshooting** — three entries:
  - Process hangs → missing `break` on `turn.completed`
  - Auth error → add `OPENAI_API_KEY` to `.env` or run `codex auth login`
  - `bun: command not found` → install Bun

- **VALIDATE**: `grep -n "Codex SDK Harness" README.md` returns a result; confirm
  `OPENAI_API_KEY` appears in the auth section; confirm `turn.completed` hang warning is present

---

## TESTING STRATEGY

### Manual End-to-End Test
1. Ensure `.env` has valid `JIRA_API_TOKEN`
2. Run: `bun run codex-harness/index.ts`
3. Verify terminal shows `[AGENT] Command: ...` lines (streaming shell commands)
4. Verify `reports/` directory created with 3 files
5. Open `reports/jira_status_report.html` — confirm renders correctly
6. Run: `bun run codex-harness/index.ts --detailed-report`
7. Verify Report Link and Log Files columns in HTML

### Edge Cases to Verify
- Missing `JIRA_API_TOKEN` → harness exits before calling agent
- Streaming `error` event → logged and loop continues gracefully
- `fullResponse` empty (agent used tools only, no text) → falls back to default `AnalyzerResult`
- `turn.completed` break — confirm process does not hang for 90s after agent finishes

### Regression: Verify Claude Harness Unaffected
- `cd claude_jira_table_processor && bun run claude-harness/index.ts` should still work
  unchanged — the two harness folders are fully independent with no shared files

---

## VALIDATION COMMANDS

All commands run from inside `codex_jira_table_processor/`:

### Level 1: Folder + Symlink
```bash
cd /Users/jyotirdiptadas/codebase/jira-table-processor/codex_jira_table_processor
ls -la .env
```
Expected: `.env -> ../.env` symlink present

### Level 2: Dependency Install
```bash
cd /Users/jyotirdiptadas/codebase/jira-table-processor/codex_jira_table_processor
bun install
```
Expected: `node_modules/@openai/codex-sdk` present, `bun.lockb` created

### Level 3: Type Check
```bash
cd /Users/jyotirdiptadas/codebase/jira-table-processor/codex_jira_table_processor
bun run --bun tsc --noEmit
```
Expected: zero errors

### Level 4: Auth Check
```bash
codex auth status
```
Expected: authenticated (run `codex auth login` if not — or add `OPENAI_API_KEY` to `.env`)

### Level 5: Dry-Run
```bash
cd /Users/jyotirdiptadas/codebase/jira-table-processor/codex_jira_table_processor
JIRA_API_TOKEN=fake JQL_QUERY="project = TEST" bun run codex-harness/index.ts
```
Expected: harness starts, agent runs, reports JIRA failure gracefully — does NOT hang

### Level 6: Full Run
```bash
cd /Users/jyotirdiptadas/codebase/jira-table-processor/codex_jira_table_processor
bun run codex-harness/index.ts
```
Expected: `../reports/jira_status_report.html` created (in the project root `reports/` folder)

### Level 7: Detailed Report Flag
```bash
cd /Users/jyotirdiptadas/codebase/jira-table-processor/codex_jira_table_processor
bun run codex-harness/index.ts --detailed-report
```
Expected: `../reports/jira_status_report.html` includes Report Link and Log Files columns

---

## ACCEPTANCE CRITERIA

- [ ] `codex_jira_table_processor/.env` is a symlink to `../.env`
- [ ] `bun install` (from inside `codex_jira_table_processor/`) completes without errors
- [ ] `bun run --bun tsc --noEmit` passes with zero errors
- [ ] Missing `JIRA_API_TOKEN` exits with a clear error before invoking the agent
- [ ] Running the harness with a valid `.env` produces all 3 report files in project root `reports/`
- [ ] `--detailed-report` flag passed through correctly to the Python script
- [ ] Streaming output shows `[AGENT] Command:` lines during execution
- [ ] Process does NOT hang after the agent finishes (confirming `break` on `turn.completed`)
- [ ] `process.exit(0)` on success, `process.exit(1)` on failure
- [ ] No TypeScript `any` usage without cast (strict mode on)
- [ ] Existing `jira_table_analyze.py` and `report_env/` are not modified
- [ ] `claude_jira_table_processor/` is completely unaffected (independent folder)
- [ ] `README.md` updated with Codex SDK harness section documenting `codex_jira_table_processor/`

---

## COMPLETION CHECKLIST

- [ ] `codex_jira_table_processor/` folder created with `.env` symlink
- [ ] `codex_jira_table_processor/package.json` with `@openai/codex-sdk`
- [ ] `codex_jira_table_processor/tsconfig.json`
- [ ] `codex_jira_table_processor/shared/config.ts` — `CODEX_MODEL`, `CODEX_NETWORK_ACCESS`, `DEFAULT_CONFIG`
- [ ] `codex_jira_table_processor/shared/types.ts` — `AnalyzerConfig`, `EmailConfig`, `AnalyzerResult`
- [ ] `codex_jira_table_processor/shared/prompts.ts` — `JIRA_ANALYZER_SYSTEM_PROMPT`
- [ ] `codex_jira_table_processor/codex-harness/analyzer.ts` — `runAnalyzer()` with `runStreamed()` + `break`
- [ ] `codex_jira_table_processor/codex-harness/index.ts` — args, env, date-subject logic, orchestration
- [ ] `README.md` — Codex SDK section updated to reference `codex_jira_table_processor/`
- [ ] All type checks pass
- [ ] End-to-end run produces correct output in project root `reports/`

---

## NOTES

### Critical: The 90-Second Timeout
From `adversarial-dev/codex-harness/generator.ts` line comment: "Critical: break on turn.completed
to prevent 90s timeout". The Codex SDK's `runStreamed()` event stream does not close itself after
the turn ends — you **must** explicitly `break` when you receive `event.type === "turn.completed"`.
Forgetting this causes the process to hang for 90 seconds before timing out.

### Why `runStreamed()` Instead of `thread.run()`
The synchronous `thread.run()` is simpler (`turn.finalResponse` is immediately available) but
gives zero visibility during execution. For a task that may take 30–60 seconds (JIRA fetch +
remote links enrichment for many tickets), streaming is strongly preferred so the operator can
see the agent's shell commands in real time.

### No Explicit Tool List
Unlike the Claude SDK (where you specify `tools: ["Bash", "Write", ...]`), the Codex SDK grants
all capabilities implicitly via `sandboxMode: "danger-full-access"`. The agent can read/write
files and execute shell commands without any configuration.

### System Prompt Prepending
Codex has no `systemPrompt` option. The pattern is:
```typescript
const fullPrompt = `${SYSTEM_PROMPT}\n\n---\n\n${userPrompt}`;
```
The `---` separator is a visual boundary used consistently across all `adversarial-dev` Codex files.

### Self-Contained Harness Folders
`codex_jira_table_processor/` and `claude_jira_table_processor/` are fully independent — each
has its own `node_modules/`, `package.json`, `shared/`, and `bun.lockb`. There are no
cross-folder imports. This keeps the two implementations isolated and independently runnable.

### workDir
`workDir: resolve("..")` — one level up from `codex_jira_table_processor/` — resolves to the
project root where `jira_table_analyze.py` and `report_env/` live. This is passed to both
`config.workDir` (for the prompt) and `startThread({ workingDirectory })` (for the agent's cwd).
All output files land in `../reports/` relative to the harness folder.

### .gitignore
Add to existing `.gitignore` at project root (do NOT create a new one):
```
codex_jira_table_processor/node_modules/
codex_jira_table_processor/bun.lockb
codex_jira_table_processor/.env
```

---

**Confidence Score: 9.5/10**

All Codex SDK patterns verified line-by-line from `adversarial-dev/codex-harness/`. The only
uncertainty is whether `gpt-5.4` requires a different network setup or API key compared to what
`codex auth login` provides — but this is an auth concern, not an implementation one.
