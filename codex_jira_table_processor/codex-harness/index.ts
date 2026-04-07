import { resolve } from "path";
import { runAnalyzer } from "./analyzer.ts";
import { DEFAULT_CONFIG } from "../shared/config.ts";
import type { AnalyzerConfig, EmailConfig } from "../shared/types.ts";

// --- Arg parsing ---
const detailedReport = process.argv.includes("--detailed-report");

// --- Env + validation ---
const jiraUrl    = process.env["JIRA_URL"]        ?? "https://jira-sd.mc1.oracleiaas.com";
const apiToken   = process.env["JIRA_API_TOKEN"]  ?? "";
const jqlQuery   = process.env["JQL_QUERY"]       ?? "";
const maxResults = parseInt(process.env["MAX_RESULTS"] ?? "100", 10);

if (!apiToken) {
  console.error("ERROR: JIRA_API_TOKEN is not set. Please configure .env.");
  process.exit(1);
}

// --- Date-range subject logic (mirrors jira_table_analyze.py lines 953–958) ---
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

// --- Email config assembly ---
const smtpServer = process.env["EMAIL_SMTP_SERVER"];
const emailFrom  = process.env["EMAIL_FROM"];
const emailTo    = process.env["EMAIL_TO"];
const emailConfig: EmailConfig | undefined =
  smtpServer && emailFrom && emailTo
    ? { smtpServer, from: emailFrom, to: emailTo, subject: emailSubject }
    : undefined;

// --- Full config ---
const config: AnalyzerConfig = {
  ...DEFAULT_CONFIG,
  jiraUrl,
  apiToken,
  jqlQuery,
  maxResults,
  detailedReport,
  workDir: resolve("."),    // codex_jira_table_processor/ — agent runs here, reports/ lands here
  emailConfig,
};

// --- Orchestration ---
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
  if (result.outputFiles.length > 0) {
    console.log("[HARNESS] Output files:");
    for (const f of result.outputFiles) {
      console.log(`[HARNESS]   ${f}`);
    }
  }
  process.exit(result.success ? 0 : 1);
} catch (error) {
  console.error(`[HARNESS] Fatal: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
}
