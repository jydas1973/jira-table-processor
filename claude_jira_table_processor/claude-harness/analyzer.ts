import { query, type Options } from "@anthropic-ai/claude-agent-sdk";
import { JIRA_ANALYZER_SYSTEM_PROMPT } from "../shared/prompts.ts";
import { CLAUDE_MODEL, CLAUDE_MAX_TURNS } from "../shared/config.ts";
import type { AnalyzerConfig, AnalyzerResult } from "../shared/types.ts";

export async function runAnalyzer(config: AnalyzerConfig): Promise<AnalyzerResult> {
  const startTime = Date.now();

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

  let fullResponse = "";

  console.log("[HARNESS] Invoking Claude agent...");

  for await (const msg of query({ prompt, options })) {
    if (msg.type === "assistant") {
      const message = msg as { message: { content: Array<{ type: string; text?: string; name?: string }> } };
      for (const block of message.message.content) {
        if (block.type === "text" && block.text) {
          fullResponse += block.text;
        } else if (block.type === "tool_use" && block.name) {
          console.log(`[AGENT]   Tool: ${block.name}`);
        }
      }
    } else if (msg.type === "result") {
      const result = msg as { session_id?: string };
      console.log(`[AGENT]   Done (session: ${result.session_id?.slice(0, 8)}...)`);
    }
  }

  if (!fullResponse) {
    console.log("[AGENT]   Agent completed (no text output — used tools only)");
  }

  const durationMs = Date.now() - startTime;

  // Parse JSON summary from agent response using multi-strategy extraction
  const parsed = parseAgentResult(fullResponse);

  return {
    success: parsed.success,
    durationMs,
    outputFiles: parsed.files ?? [],
    emailSent: parsed.emailSent ?? false,
  };
}

interface AgentSummary {
  success: boolean;
  files?: string[];
  emailSent?: boolean;
}

function parseAgentResult(text: string): AgentSummary {
  const candidates: string[] = [];

  // Strategy 1: last JSON code block
  const codeBlocks = [...text.matchAll(/```(?:json)?\s*([\s\S]*?)```/g)];
  for (const match of codeBlocks.reverse()) {
    if (match[1]) candidates.push(match[1].trim());
  }

  // Strategy 2: { ... } object with "success" key
  const braceMatch = text.match(/\{[\s\S]*?"success"[\s\S]*?\}/);
  if (braceMatch) candidates.push(braceMatch[0]);

  // Strategy 3: entire text
  candidates.push(text.trim());

  for (const candidate of candidates) {
    try {
      const parsed = JSON.parse(candidate) as AgentSummary;
      if (typeof parsed.success === "boolean") {
        return parsed;
      }
    } catch {
      // Try next candidate
    }
  }

  // Default: could not parse — assume failure
  console.log("[HARNESS] Could not parse agent JSON summary, defaulting to failure");
  return { success: false };
}
