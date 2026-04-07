import type { AnalyzerConfig } from "./types.ts";

export const CLAUDE_MODEL = "claude-sonnet-4-6";
export const CLAUDE_MAX_TURNS = 10;

export const DEFAULT_CONFIG: Pick<AnalyzerConfig, "maxResults" | "detailedReport"> = {
  maxResults: 100,
  detailedReport: false,
};
