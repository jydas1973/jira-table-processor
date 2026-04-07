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
