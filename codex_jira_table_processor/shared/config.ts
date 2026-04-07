import type { AnalyzerConfig } from "./types.ts";

export const CODEX_MODEL = "oca/gpt-5.3-codex";
export const CODEX_NETWORK_ACCESS = true;

export const DEFAULT_CONFIG: Pick<AnalyzerConfig, "maxResults" | "detailedReport"> = {
  maxResults: 100,
  detailedReport: false,
};
