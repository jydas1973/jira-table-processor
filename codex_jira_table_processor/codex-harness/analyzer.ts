import { Codex } from "@openai/codex-sdk";
import { JIRA_ANALYZER_SYSTEM_PROMPT } from "../shared/prompts.ts";
import { CODEX_MODEL, CODEX_NETWORK_ACCESS } from "../shared/config.ts";
import type { AnalyzerConfig, AnalyzerResult } from "../shared/types.ts";

export async function runAnalyzer(config: AnalyzerConfig): Promise<AnalyzerResult> {
  const startTime = Date.now();

  const taskPrompt = `
Run a complete JIRA analysis with the following parameters:
- JIRA URL: ${config.jiraUrl}
- JQL Query: ${config.jqlQuery}
- Max Results: ${config.maxResults}
- Detailed Report: ${config.detailedReport}
- Working Directory: ${config.workDir}
${
  config.emailConfig
    ? `- Email: send to ${config.emailConfig.to} via ${config.emailConfig.smtpServer}`
    : "- Email: not configured, skip"
}

Execute the workflow now.
`.trim();

  const fullPrompt = `${JIRA_ANALYZER_SYSTEM_PROMPT}\n\n---\n\n${taskPrompt}`;

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
      if (u) {
        console.log(`[AGENT]   Tokens: ${u.input_tokens ?? 0} in / ${u.output_tokens ?? 0} out`);
      }
      console.log("[AGENT]   Turn complete");
      break; // CRITICAL: must break here — skipping causes a 90-second hang
    } else if (event.type === "error") {
      const e = event as { message?: string };
      console.error(`[AGENT]   Stream error: ${e.message ?? "unknown"}`);
    }
  }

  const durationMs = Date.now() - startTime;

  return parseResult(fullResponse, durationMs);
}

function parseResult(fullResponse: string, durationMs: number): AnalyzerResult {
  const fallback: AnalyzerResult = {
    success: false,
    durationMs,
    outputFiles: [],
    emailSent: false,
  };

  if (!fullResponse) {
    return fallback;
  }

  // Strategy 1: last JSON code block
  const codeBlockMatches = [...fullResponse.matchAll(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/g)];
  if (codeBlockMatches.length > 0) {
    const lastMatch = codeBlockMatches[codeBlockMatches.length - 1];
    try {
      const parsed = JSON.parse(lastMatch![1]!) as Record<string, unknown>;
      if (typeof parsed["success"] === "boolean") {
        return {
          success: parsed["success"],
          durationMs,
          outputFiles: Array.isArray(parsed["files"]) ? (parsed["files"] as string[]) : [],
          emailSent: typeof parsed["emailSent"] === "boolean" ? parsed["emailSent"] : false,
        };
      }
    } catch {
      // fall through
    }
  }

  // Strategy 2: inline {...} containing "success"
  const inlineMatch = fullResponse.match(/\{[^{}]*"success"[^{}]*\}/);
  if (inlineMatch) {
    try {
      const parsed = JSON.parse(inlineMatch[0]) as Record<string, unknown>;
      if (typeof parsed["success"] === "boolean") {
        return {
          success: parsed["success"],
          durationMs,
          outputFiles: Array.isArray(parsed["files"]) ? (parsed["files"] as string[]) : [],
          emailSent: typeof parsed["emailSent"] === "boolean" ? parsed["emailSent"] : false,
        };
      }
    } catch {
      // fall through
    }
  }

  // Strategy 3: infer from text content
  const lowerResponse = fullResponse.toLowerCase();
  if (lowerResponse.includes("analysis complete") || lowerResponse.includes('"success": true')) {
    return {
      success: true,
      durationMs,
      outputFiles: [
        "reports/jira_table.csv",
        "reports/jira_status_report.csv",
        "reports/jira_status_report.html",
      ],
      emailSent: lowerResponse.includes("email sent"),
    };
  }

  return fallback;
}
