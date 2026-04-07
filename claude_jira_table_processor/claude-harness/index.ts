import { resolve } from "path";
import { runAnalyzer } from "./analyzer.ts";
import { DEFAULT_CONFIG } from "../shared/config.ts";
import type { AnalyzerConfig, EmailConfig } from "../shared/types.ts";

// Arg parsing
const detailedReport = process.argv.includes("--detailed-report");

// Env loading (Bun auto-loads .env from cwd)
const jiraUrl    = process.env["JIRA_URL"]        ?? "https://jira-sd.mc1.oracleiaas.com";
const apiToken   = process.env["JIRA_API_TOKEN"]  ?? "";
const jqlQuery   = process.env["JQL_QUERY"]       ?? "";
const maxResults = parseInt(process.env["MAX_RESULTS"] ?? "100", 10);

// Validation: API token is required
if (!apiToken) {
  console.error("[HARNESS] Error: JIRA_API_TOKEN is not set.");
  console.error("[HARNESS] Please set JIRA_API_TOKEN in your .env file or environment.");
  console.error("[HARNESS] Example: JIRA_API_TOKEN=your_token_here");
  process.exit(1);
}

// Date-range subject logic (mirrors jira_table_analyze.py lines 953–958)
let emailSubject = process.env["EMAIL_SUBJECT"] ?? "JIRA Status Report";
const createdMatch = jqlQuery.match(/created\s*>=\s*-(\d+)d/i);
if (createdMatch) {
  const daysBack = parseInt(createdMatch[1]!, 10);
  const today = new Date();
  const fromDate = new Date(today.getTime() - daysBack * 86400000);
  const fmt = (d: Date) => d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  emailSubject = `${emailSubject} from ${fmt(fromDate)} to ${fmt(today)}`;
}

// Email config assembly
const smtpServer = process.env["EMAIL_SMTP_SERVER"];
const emailFrom  = process.env["EMAIL_FROM"];
const emailTo    = process.env["EMAIL_TO"];
let emailConfig: EmailConfig | undefined;
if (smtpServer && emailFrom && emailTo) {
  emailConfig = { smtpServer, from: emailFrom, to: emailTo, subject: emailSubject };
}

// Config assembly
const config: AnalyzerConfig = {
  ...DEFAULT_CONFIG,
  jiraUrl,
  apiToken,
  jqlQuery,
  maxResults,
  detailedReport,
  workDir: resolve("."),    // claude_jira_table_processor/ — reports/ is created here
  emailConfig,
};

// Orchestration
console.log("=".repeat(80));
console.log("[HARNESS] JIRA Claude SDK Harness");
console.log(`[HARNESS] JIRA: ${jiraUrl}`);
console.log(`[HARNESS] JQL:  ${jqlQuery}`);
console.log(`[HARNESS] Max:  ${maxResults} | Detailed: ${detailedReport}`);
if (emailConfig) {
  console.log(`[HARNESS] Email: ${emailConfig.to} (via ${emailConfig.smtpServer})`);
} else {
  console.log("[HARNESS] Email: not configured");
}
console.log("=".repeat(80));

try {
  const result = await runAnalyzer(config);

  console.log("=".repeat(80));
  console.log(result.success ? "[HARNESS] Analysis complete!" : "[HARNESS] Analysis failed.");
  console.log(`[HARNESS] Duration: ${(result.durationMs / 1000).toFixed(1)}s`);
  if (result.outputFiles.length > 0) {
    console.log(`[HARNESS] Output files:`);
    for (const f of result.outputFiles) {
      console.log(`[HARNESS]   ${f}`);
    }
  }
  if (result.emailSent) {
    console.log("[HARNESS] Email sent successfully.");
  }
  console.log("=".repeat(80));

  process.exit(result.success ? 0 : 1);
} catch (error) {
  console.error(`[HARNESS] Fatal: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
}
