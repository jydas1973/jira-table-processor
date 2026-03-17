#!/usr/bin/env python3
"""
JIRA Table Analyzer
This program queries JIRA directly using JQL filter and processes the data to create status reports.
No image scanning required - data is fetched directly from JIRA API.
"""

import pandas as pd
import os
import sys
from typing import Tuple, List, Dict, Optional
import re
from jira import JIRA
from dotenv import load_dotenv
import shutil
from datetime import datetime, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class JiraTableAnalyzer:
    def __init__(self, jira_url: str, api_token: str):
        """
        Initialize the analyzer with JIRA connection details.

        Args:
            jira_url: JIRA instance URL (e.g., 'https://jira-sd.mc1.oracleiaas.com')
            api_token: JIRA API token from .env file
        """
        self.jira_url = jira_url
        self.jira = None
        self.df = pd.DataFrame()
        self.status_df = pd.DataFrame()

        # Connect to JIRA
        self._connect(api_token)

    def _connect(self, api_token: str):
        """Establish connection to JIRA."""
        try:
            print(f"Connecting to JIRA at {self.jira_url}...")
            jira_options = {'server': self.jira_url}
            self.jira = JIRA(
                options=jira_options,
                token_auth=api_token
            )
            print("✓ Successfully connected to JIRA")
        except Exception as e:
            print(f"✗ Failed to connect to JIRA: {e}")
            raise

    def fetch_remote_links(self, key: str) -> Dict:
        """
        Fetch remote links for a JIRA issue and extract the triage report URL and log file names.

        Returns:
            Dict with keys 'report_url' (str or None) and 'log_files' (list of filenames)
        """
        result = {'report_url': None, 'log_files': []}
        try:
            remote_links = self.jira.remote_links(key)
            for rl in remote_links:
                obj = rl.object
                title = getattr(obj, 'title', '') or ''
                url = getattr(obj, 'url', '') or ''
                if title == 'VoxioTriageX - Triage Report':
                    result['report_url'] = url
                elif title.startswith('TriageX - Log '):
                    filename = title[len('TriageX - Log '):]
                    result['log_files'].append(filename)
        except Exception as e:
            print(f"  ⚠ Could not fetch remote links for {key}: {e}")
        return result

    def enrich_with_remote_links(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fetch remote links for each issue and add 'Report Link' and 'Log Files' columns."""
        print(f"\n[Detailed Report] Fetching remote links for {len(df)} issues...")
        report_urls = []
        log_files_list = []
        for key in df['Key']:
            links = self.fetch_remote_links(key)
            report_urls.append(links['report_url'] or '')
            log_files_list.append(', '.join(links['log_files']))
            print(f"  ✓ {key}: report={'yes' if links['report_url'] else 'no'}, logs={len(links['log_files'])}")
        df = df.copy()
        df['Report Link'] = report_urls
        df['Log Files'] = log_files_list
        return df

    def fetch_issues_from_jira(self, jql_query: str, max_results: int = 100) -> pd.DataFrame:
        """
        Fetch issues from JIRA using JQL query.

        Args:
            jql_query: JQL filter string
            max_results: Maximum number of results to fetch (default: 100)

        Returns:
            DataFrame with issue data
        """
        print(f"\nExecuting JQL query:")
        print(f"  {jql_query}")
        print(f"  Max results: {max_results}\n")

        try:
            # Search for issues
            issues = self.jira.search_issues(
                jql_query,
                maxResults=max_results,
                fields='key,summary,assignee,reporter,priority,status,resolution,created,updated,duedate,labels'
            )

            print(f"✓ Found {len(issues)} issues")

            # Convert to structured data
            data = []
            for issue in issues:
                # Extract assignee name (handle unassigned)
                assignee = issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned'

                # Extract reporter name
                reporter = issue.fields.reporter.displayName if issue.fields.reporter else 'Unknown'

                # Extract priority
                priority = issue.fields.priority.name if issue.fields.priority else ''

                # Extract labels as space-separated string
                labels = ' '.join(issue.fields.labels) if issue.fields.labels else ''

                # Format dates
                created = issue.fields.created.split('T')[0] if issue.fields.created else ''
                updated = issue.fields.updated.split('T')[0] if issue.fields.updated else ''
                due = issue.fields.duedate if issue.fields.duedate else ''

                data.append({
                    'Key': issue.key,
                    'Summary': issue.fields.summary,
                    'Assignee': assignee,
                    'Reporter': reporter,
                    'P': priority,
                    'Status': issue.fields.status.name,
                    'Resolution': issue.fields.resolution.name if issue.fields.resolution else 'Unresolved',
                    'Created': created,
                    'Updated': updated,
                    'Due': due,
                    'Labels': labels
                })

            self.df = pd.DataFrame(data)
            return self.df

        except Exception as e:
            print(f"✗ Error fetching issues: {e}")
            return pd.DataFrame()

    def save_to_csv(self, df: pd.DataFrame, output_path: str) -> str:
        """Save DataFrame to CSV."""
        df.to_csv(output_path, index=False)
        print(f"✓ Saved table to {output_path}")
        return output_path

    def print_table(self, df: pd.DataFrame) -> None:
        """Print the table in a human-readable format."""
        print("\n" + "=" * 150)
        print("JIRA ISSUES TABLE")
        print("=" * 150)
        if df.empty:
            print("No data to display.")
        else:
            # Set display options for better formatting
            pd.set_option('display.max_columns', None)
            pd.set_option('display.max_colwidth', 50)
            pd.set_option('display.width', None)
            print(df.to_string(index=False))
        print("=" * 150 + "\n")

    def process_labels_and_create_status_report(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Analyzes labels to determine status and creates a summary report.

        Args:
            df: DataFrame with JIRA issues

        Returns:
            DataFrame with JIRA ID, Status, Date, and Link
        """
        report_data = []

        for index, row in df.iterrows():
            key = row['Key']
            labels = str(row['Labels']).lower() if pd.notna(row['Labels']) else ''
            created_date = row['Created'] if pd.notna(row['Created']) else ''

            # Generate JIRA link
            link = f"{self.jira_url}/browse/{key}"

            # Analyze labels for status
            status = None
            if 'oneview_triagex_failed' in labels:
                status = "Failed"
            elif 'oneview_triagex_success' in labels:
                status = "Success"

            # Only add to report if status is found
            if status:
                entry = {
                    "JIRA ID": key,
                    "Status": status,
                    "Date": created_date,
                    "Link": link
                }
                if 'Report Link' in df.columns:
                    entry['Report Link'] = row.get('Report Link', '')
                if 'Log Files' in df.columns:
                    entry['Log Files'] = row.get('Log Files', '')
                report_data.append(entry)

        self.status_df = pd.DataFrame(report_data)
        return self.status_df

    def print_status_report(self, status_df: pd.DataFrame) -> None:
        """Print the status report in a formatted way."""
        print("\n" + "=" * 100)
        print("JIRA STATUS REPORT")
        print("=" * 100)
        if not status_df.empty:
            print(status_df.to_string(index=False))
            print("=" * 100)
            print("\nSummary:")
            total = len(status_df)
            success = len(status_df[status_df['Status'] == 'Success'])
            failed = len(status_df[status_df['Status'] == 'Failed'])
            success_pct = (success / total * 100) if total > 0 else 0
            failed_pct = (failed / total * 100) if total > 0 else 0
            print(f"  Total Issues: {total}")
            print(f"  Success: {success} ({success_pct:.1f}%)")
            print(f"  Failed: {failed} ({failed_pct:.1f}%)")
        else:
            print("No matching issues found with success/failed labels.")
        print("=" * 100 + "\n")

    def save_status_report_to_csv(self, status_df: pd.DataFrame, output_path: str) -> str:
        """Save status report to CSV."""
        status_df.to_csv(output_path, index=False)
        print(f"✓ Saved status report to {output_path}")
        return output_path

    def create_html_report(self, status_df: pd.DataFrame, output_path: str, jql_query: str = None) -> str:
        """Create an HTML report with clickable hyperlinks and styling."""
        if status_df.empty:
            html_content = """
            <html>
            <head>
                <title>JIRA Status Report</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    h1 { color: #333; }
                </style>
            </head>
            <body>
                <h1>JIRA Status Report</h1>
                <p>No issues found with success/failed labels.</p>
            </body>
            </html>
            """
        else:
            # Calculate statistics
            total = len(status_df)
            success_df = status_df[status_df['Status'] == 'Success']
            failed_df = status_df[status_df['Status'] == 'Failed']
            success = len(success_df)
            failed = len(failed_df)

            # Calculate percentages
            success_pct = (success / total * 100) if total > 0 else 0
            failed_pct = (failed / total * 100) if total > 0 else 0

            # Generate success list HTML (comma-separated)
            success_list_html = ""
            if success > 0:
                success_links = []
                for _, row in success_df.iterrows():
                    success_links.append(f'<a href="{row["Link"]}" target="_blank" style="color: #0052CC; text-decoration: none; font-weight: 500;">{row["JIRA ID"]}</a>')
                success_list_html = f"<p style='margin: 10px 0; line-height: 1.6;'>{', '.join(success_links)}</p>"
            else:
                success_list_html = "<p style='margin: 10px 0; color: #666;'>None</p>"

            # Generate failed list HTML (comma-separated)
            failed_list_html = ""
            if failed > 0:
                failed_links = []
                for _, row in failed_df.iterrows():
                    failed_links.append(f'<a href="{row["Link"]}" target="_blank" style="color: #0052CC; text-decoration: none; font-weight: 500;">{row["JIRA ID"]}</a>')
                failed_list_html = f"<p style='margin: 10px 0; line-height: 1.6;'>{', '.join(failed_links)}</p>"
            else:
                failed_list_html = "<p style='margin: 10px 0; color: #666;'>None</p>"

            # Detect whether detailed columns are present
            has_detail = 'Report Link' in status_df.columns and 'Log Files' in status_df.columns

            # Generate table rows
            rows_html = ""
            for _, row in status_df.iterrows():
                if row['Status'] == 'Success':
                    status_class = "status-success"
                    status_text = "SUCCESS"
                    status_inline = "display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.3px; background-color: #e3fcef; color: #006644;"
                else:
                    status_class = "status-failed"
                    status_text = "FAILED"
                    status_inline = "display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.3px; background-color: #ffebe6; color: #bf2600;"

                # Build optional detail cells
                report_cell = ""
                log_files_cell = ""
                if has_detail:
                    report_url = row.get('Report Link', '')
                    if report_url:
                        report_cell = f'<td><a href="{report_url}" target="_blank" class="jira-link">Report</a></td>'
                    else:
                        report_cell = '<td style="color:#999;">-</td>'

                    log_files_raw = row.get('Log Files', '')
                    files = [f.strip() for f in log_files_raw.split(',') if f.strip()] if log_files_raw else []
                    if files:
                        visible = files[:2]
                        hidden = files[2:]
                        visible_html = ''.join(f'<div class="log-file">{f}</div>' for f in visible)
                        if hidden:
                            hidden_html = ''.join(f'<div class="log-file">{f}</div>' for f in hidden)
                            log_content = f'''{visible_html}<details class="log-details"><summary>+{len(hidden)} more</summary>{hidden_html}</details>'''
                        else:
                            log_content = visible_html
                        log_files_cell = f'<td class="log-files-cell">{log_content}</td>'
                    else:
                        log_files_cell = '<td style="color:#999;">-</td>'

                rows_html += f"""
                <tr>
                    <td>
                        <a href="{row['Link']}" target="_blank" class="jira-link">
                            {row['JIRA ID']}
                        </a>
                    </td>
                    <td>
                        <span class="status-badge {status_class}" style="{status_inline}">
                            {status_text}
                        </span>
                    </td>
                    <td>
                        {row['Date']}
                    </td>
                    {report_cell}
                    {log_files_cell}
                </tr>
                """

            # Generate JQL query section if provided
            jql_section_html = ""
            if jql_query:
                jql_section_html = f"""
                <div class="jql-query">
                    <h3>JQL Query</h3>
                    <pre>{jql_query}</pre>
                </div>
                """

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>JIRA Status Report</title>
                <meta charset="UTF-8">
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
                        margin: 0;
                        padding: 20px;
                        background-color: #f4f5f7;
                        color: #172b4d;
                        font-size: 14px;
                        line-height: 1.5;
                    }}
                    h1 {{
                        color: #172b4d;
                        text-align: center;
                        margin-bottom: 30px;
                        font-size: 24px;
                        font-weight: 500;
                    }}
                    .jql-query {{
                        margin: 0 auto 20px;
                        max-width: 900px;
                        background-color: white;
                        padding: 16px 20px;
                        border-radius: 3px;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                        border: 1px solid #dfe1e6;
                        border-left: 3px solid #0052CC;
                    }}
                    .jql-query h3 {{
                        color: #172b4d;
                        font-size: 14px;
                        font-weight: 600;
                        margin-bottom: 8px;
                    }}
                    .jql-query pre {{
                        background-color: #f4f5f7;
                        padding: 12px;
                        border-radius: 3px;
                        font-family: 'Courier New', Courier, monospace;
                        font-size: 12px;
                        color: #172b4d;
                        overflow-x: auto;
                        white-space: pre-wrap;
                        word-wrap: break-word;
                    }}
                    .summary {{
                        margin: 0 auto 30px;
                        max-width: 900px;
                        background-color: white;
                        padding: 20px 24px;
                        border-radius: 3px;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                        border: 1px solid #dfe1e6;
                    }}
                    .summary h3 {{
                        color: #172b4d;
                        font-size: 16px;
                        font-weight: 600;
                        margin-bottom: 16px;
                        padding-bottom: 8px;
                        border-bottom: 1px solid #dfe1e6;
                    }}
                    .summary p {{
                        margin: 8px 0;
                        font-size: 14px;
                        color: #42526e;
                    }}
                    .summary strong {{
                        color: #172b4d;
                        font-weight: 600;
                    }}
                    .summary h4 {{
                        margin: 20px 0 8px 0;
                        color: #172b4d;
                        font-size: 14px;
                        font-weight: 600;
                    }}
                    .summary a {{
                        color: #0052CC;
                        text-decoration: none;
                        font-weight: 500;
                    }}
                    .summary a:hover {{
                        color: #0065FF;
                        text-decoration: underline;
                    }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        max-width: 900px;
                        margin: 0 auto;
                        background-color: white;
                        border-radius: 3px;
                        overflow: hidden;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                        border: 1px solid #dfe1e6;
                    }}
                    th {{
                        background-color: #f4f5f7;
                        color: #172b4d;
                        padding: 12px 16px;
                        text-align: left;
                        font-weight: 600;
                        font-size: 12px;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                        border-bottom: 2px solid #dfe1e6;
                    }}
                    td {{
                        padding: 12px 16px;
                        border-bottom: 1px solid #f4f5f7;
                    }}
                    tr:hover {{
                        background-color: #f4f5f7;
                    }}
                    tr:last-child td {{
                        border-bottom: none;
                    }}
                    .jira-link {{
                        color: #0052CC;
                        text-decoration: none;
                        font-weight: 500;
                        font-size: 14px;
                    }}
                    .jira-link:hover {{
                        color: #0065FF;
                        text-decoration: underline;
                    }}
                    .status-badge {{
                        display: inline-block;
                        padding: 2px 8px;
                        border-radius: 3px;
                        font-size: 11px;
                        font-weight: 700;
                        text-transform: uppercase;
                        letter-spacing: 0.3px;
                    }}
                    .status-success {{
                        background-color: #e3fcef;
                        color: #006644;
                    }}
                    .status-failed {{
                        background-color: #ffebe6;
                        color: #bf2600;
                    }}
                    .log-files-cell {{
                        font-size: 12px;
                        color: #42526e;
                        min-width: 200px;
                    }}
                    .log-file {{
                        padding: 1px 0;
                        font-family: 'Courier New', Courier, monospace;
                        font-size: 11px;
                        word-break: break-all;
                    }}
                    .log-details summary {{
                        cursor: pointer;
                        color: #0052CC;
                        font-size: 11px;
                        margin-top: 4px;
                        user-select: none;
                    }}
                    .log-details summary:hover {{
                        text-decoration: underline;
                    }}
                </style>
            </head>
            <body>
                <h1>JIRA Status Report</h1>

                {jql_section_html}

                <div class="summary">
                    <h3>Summary</h3>
                    <p><strong>Total Issues:</strong> {total}</p>
                    <p><strong>Success:</strong> {success} ({success_pct:.1f}%)</p>
                    <p><strong>Failed:</strong> {failed} ({failed_pct:.1f}%)</p>

                    <h4>Successful JIRA Tickets:</h4>
                    {success_list_html}

                    <h4>Failed JIRA Tickets:</h4>
                    {failed_list_html}
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>JIRA ID</th>
                            <th>Status</th>
                            <th>Date Created</th>
                            {'<th>Report</th><th>Log Files</th>' if has_detail else ''}
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </body>
            </html>
            """

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"✓ Saved HTML report to {output_path}")
        return output_path

    def _generate_email_html(self, status_df: pd.DataFrame, jql_query: str = None) -> str:
        """
        Generate a simplified HTML email body.
        Same as the full report but the Log Files column shows only a file count
        with a note in the header directing recipients to the attached report.
        """
        if status_df.empty:
            return """
            <html><head><title>JIRA Status Report</title></head>
            <body style="font-family:Arial,sans-serif;margin:20px;">
                <h1>JIRA Status Report</h1>
                <p>No issues found with success/failed labels.</p>
            </body></html>"""

        has_detail = 'Report Link' in status_df.columns and 'Log Files' in status_df.columns

        total = len(status_df)
        success_df = status_df[status_df['Status'] == 'Success']
        failed_df  = status_df[status_df['Status'] == 'Failed']
        success    = len(success_df)
        failed     = len(failed_df)
        success_pct = (success / total * 100) if total > 0 else 0
        failed_pct  = (failed  / total * 100) if total > 0 else 0

        success_links = ', '.join(
            f'<a href="{r["Link"]}" target="_blank" style="color:#0052CC;text-decoration:none;font-weight:500;">{r["JIRA ID"]}</a>'
            for _, r in success_df.iterrows()
        ) or '<span style="color:#666;">None</span>'

        failed_links = ', '.join(
            f'<a href="{r["Link"]}" target="_blank" style="color:#0052CC;text-decoration:none;font-weight:500;">{r["JIRA ID"]}</a>'
            for _, r in failed_df.iterrows()
        ) or '<span style="color:#666;">None</span>'

        jql_section_html = ''
        if jql_query:
            jql_section_html = f"""
            <div style="margin:0 auto 20px;max-width:900px;background:#fff;padding:16px 20px;
                        border-radius:3px;box-shadow:0 1px 2px rgba(0,0,0,.1);
                        border:1px solid #dfe1e6;border-left:3px solid #0052CC;">
                <h3 style="color:#172b4d;font-size:14px;font-weight:600;margin-bottom:8px;">JQL Query</h3>
                <pre style="background:#f4f5f7;padding:12px;border-radius:3px;
                            font-family:'Courier New',monospace;font-size:12px;
                            color:#172b4d;overflow-x:auto;white-space:pre-wrap;
                            word-wrap:break-word;">{jql_query}</pre>
            </div>"""

        rows_html = ''
        for _, row in status_df.iterrows():
            if row['Status'] == 'Success':
                badge_style = 'background-color:#e3fcef;color:#006644;'
                status_text = 'SUCCESS'
            else:
                badge_style = 'background-color:#ffebe6;color:#bf2600;'
                status_text = 'FAILED'

            badge = (f'<span style="display:inline-block;padding:2px 8px;border-radius:3px;'
                     f'font-size:11px;font-weight:700;text-transform:uppercase;'
                     f'letter-spacing:0.3px;{badge_style}">{status_text}</span>')

            report_cell = ''
            log_count_cell = ''
            if has_detail:
                report_url = row.get('Report Link', '')
                if report_url:
                    report_cell = (f'<td style="padding:12px 16px;border-bottom:1px solid #f4f5f7;">'
                                   f'<a href="{report_url}" target="_blank" '
                                   f'style="color:#0052CC;text-decoration:none;font-weight:500;">Report</a></td>')
                else:
                    report_cell = '<td style="padding:12px 16px;border-bottom:1px solid #f4f5f7;color:#999;">-</td>'

                log_files_raw = row.get('Log Files', '')
                files = [f.strip() for f in log_files_raw.split(',') if f.strip()] if log_files_raw else []
                count = len(files)
                if count:
                    label = f'{count} log file' + ('s' if count != 1 else '')
                    log_count_cell = (f'<td style="padding:12px 16px;border-bottom:1px solid #f4f5f7;'
                                      f'font-size:13px;color:#42526e;">'
                                      f'<span style="display:inline-block;padding:2px 10px;'
                                      f'border-radius:10px;background:#f4f5f7;'
                                      f'border:1px solid #dfe1e6;font-size:12px;color:#42526e;">'
                                      f'{label}</span></td>')
                else:
                    log_count_cell = '<td style="padding:12px 16px;border-bottom:1px solid #f4f5f7;color:#999;">-</td>'

            rows_html += f"""
            <tr>
                <td style="padding:12px 16px;border-bottom:1px solid #f4f5f7;">
                    <a href="{row['Link']}" target="_blank"
                       style="color:#0052CC;text-decoration:none;font-weight:500;font-size:14px;">
                        {row['JIRA ID']}
                    </a>
                </td>
                <td style="padding:12px 16px;border-bottom:1px solid #f4f5f7;">{badge}</td>
                <td style="padding:12px 16px;border-bottom:1px solid #f4f5f7;">{row['Date']}</td>
                {report_cell}
                {log_count_cell}
            </tr>"""

        log_files_header = ''
        if has_detail:
            log_files_header = """
                <th style="background:#f4f5f7;color:#172b4d;padding:12px 16px;text-align:left;
                            font-weight:600;font-size:12px;text-transform:uppercase;
                            letter-spacing:0.5px;border-bottom:2px solid #dfe1e6;">
                    Log Files
                    <div style="font-size:10px;font-weight:400;text-transform:none;
                                letter-spacing:0;color:#6b778c;margin-top:3px;">
                        Full details in the attached report
                    </div>
                </th>"""

        report_header = ('<th style="background:#f4f5f7;color:#172b4d;padding:12px 16px;text-align:left;'
                         'font-weight:600;font-size:12px;text-transform:uppercase;'
                         'letter-spacing:0.5px;border-bottom:2px solid #dfe1e6;">Report</th>'
                         if has_detail else '')

        th = ('background:#f4f5f7;color:#172b4d;padding:12px 16px;text-align:left;'
              'font-weight:600;font-size:12px;text-transform:uppercase;'
              'letter-spacing:0.5px;border-bottom:2px solid #dfe1e6;')

        return f"""<!DOCTYPE html>
<html>
<head><title>JIRA Status Report</title><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Roboto',sans-serif;
             margin:0;padding:20px;background-color:#f4f5f7;color:#172b4d;font-size:14px;">
    <h1 style="color:#172b4d;text-align:center;margin-bottom:30px;font-size:24px;font-weight:500;">
        JIRA Status Report
    </h1>

    {jql_section_html}

    <div style="margin:0 auto 30px;max-width:900px;background:#fff;padding:20px 24px;
                border-radius:3px;box-shadow:0 1px 2px rgba(0,0,0,.1);border:1px solid #dfe1e6;">
        <h3 style="color:#172b4d;font-size:16px;font-weight:600;margin-bottom:16px;
                   padding-bottom:8px;border-bottom:1px solid #dfe1e6;">Summary</h3>
        <p style="margin:8px 0;font-size:14px;color:#42526e;">
            <strong style="color:#172b4d;">Total Issues:</strong> {total}</p>
        <p style="margin:8px 0;font-size:14px;color:#42526e;">
            <strong style="color:#172b4d;">Success:</strong> {success} ({success_pct:.1f}%)</p>
        <p style="margin:8px 0;font-size:14px;color:#42526e;">
            <strong style="color:#172b4d;">Failed:</strong> {failed} ({failed_pct:.1f}%)</p>
        <h4 style="margin:20px 0 8px;color:#172b4d;font-size:14px;font-weight:600;">
            Successful JIRA Tickets:</h4>
        <p style="margin:10px 0;line-height:1.6;">{success_links}</p>
        <h4 style="margin:20px 0 8px;color:#172b4d;font-size:14px;font-weight:600;">
            Failed JIRA Tickets:</h4>
        <p style="margin:10px 0;line-height:1.6;">{failed_links}</p>
    </div>

    <table style="border-collapse:collapse;width:100%;max-width:900px;margin:0 auto;
                  background:#fff;border-radius:3px;overflow:hidden;
                  box-shadow:0 1px 2px rgba(0,0,0,.1);border:1px solid #dfe1e6;">
        <thead>
            <tr>
                <th style="{th}">JIRA ID</th>
                <th style="{th}">Status</th>
                <th style="{th}">Date Created</th>
                {report_header}
                {log_files_header}
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>
</body>
</html>"""

    def send_email_report(self, html_report_path: str, smtp_server: str, email_from: str, email_to: str, email_subject: str, jql_query: str = None) -> None:
        """
        Send the HTML report as an email with the HTML content as body and the file as attachment.

        Args:
            html_report_path: Path to the HTML report file
            smtp_server: SMTP server hostname
            email_from: Sender email address
            email_to: Comma-separated recipient email addresses
            email_subject: Email subject line
            jql_query: JQL query string for display in email body
        """
        try:
            # Generate simplified email body (log files as count, not full list)
            html_content = self._generate_email_html(self.status_df, jql_query)

            # Parse recipient list
            recipients = [addr.strip() for addr in email_to.split(',') if addr.strip()]

            if not recipients:
                print("✗ No valid recipients found. Skipping email.")
                return

            # Build the email
            msg = MIMEMultipart()
            msg['From'] = email_from
            msg['To'] = email_to
            msg['Subject'] = email_subject

            # Attach HTML body
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # Attach the HTML report file
            with open(html_report_path, 'rb') as f:
                attachment = MIMEBase('text', 'html')
                attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{os.path.basename(html_report_path)}"'
                )
                msg.attach(attachment)

            # Send the email via plain SMTP on port 25
            print(f"\nSending email via {smtp_server}:25...")
            print(f"  From: {email_from}")
            print(f"  To: {email_to}")
            print(f"  Subject: {email_subject}")

            with smtplib.SMTP(smtp_server, 25) as server:
                server.sendmail(email_from, recipients, msg.as_string())

            print("✓ Email sent successfully")

        except Exception as e:
            print(f"✗ Failed to send email: {e}")

    def run(self, jql_query: str, max_results: int = 100, email_config: Optional[Dict[str, str]] = None, detailed_report: bool = False):
        """
        Execute the complete workflow.

        Args:
            jql_query: JQL filter string
            max_results: Maximum number of results to fetch
            email_config: Optional dict with keys 'smtp_server', 'from', 'to', 'subject' for sending email
        """
        print("\n" + "="*80)
        print("JIRA TABLE ANALYZER - Starting Analysis")
        print("="*80)

        # Create reports directory and clean it if it exists
        reports_dir = 'reports'
        if os.path.exists(reports_dir):
            print(f"\n[Setup] Cleaning existing {reports_dir}/ directory...")
            shutil.rmtree(reports_dir)
        print(f"[Setup] Creating {reports_dir}/ directory...")
        os.makedirs(reports_dir)
        print(f"✓ {reports_dir}/ directory ready")

        # 1. Fetch issues from JIRA
        print("\n[Step 1] Fetching issues from JIRA...")
        self.df = self.fetch_issues_from_jira(jql_query, max_results)

        if self.df.empty:
            print("✗ No data retrieved. Exiting.")
            return

        # 1b. Enrich with remote links if detailed report requested
        if detailed_report:
            self.df = self.enrich_with_remote_links(self.df)

        # 2. Save original data to CSV
        print("\n[Step 2] Saving original data to CSV...")
        self.save_to_csv(self.df, 'reports/jira_table.csv')

        # 3. Print original table
        print("\n[Step 3] Displaying original table...")
        self.print_table(self.df)

        # 4. Process labels and create status report
        print("\n[Step 4] Processing labels and creating status report...")
        self.status_df = self.process_labels_and_create_status_report(self.df)

        # 5. Save status report to CSV
        print("\n[Step 5] Saving status report to CSV...")
        self.save_status_report_to_csv(self.status_df, 'reports/jira_status_report.csv')

        # 6. Create HTML report with hyperlinks
        print("\n[Step 6] Creating HTML report with hyperlinks...")
        self.create_html_report(self.status_df, 'reports/jira_status_report.html', jql_query)

        # 7. Print final status report
        print("\n[Step 7] Displaying final status report...")
        self.print_status_report(self.status_df)

        # 8. Send email report if configured
        if email_config:
            print("\n[Step 8] Sending email report...")
            self.send_email_report(
                html_report_path='reports/jira_status_report.html',
                smtp_server=email_config['smtp_server'],
                email_from=email_config['from'],
                email_to=email_config['to'],
                email_subject=email_config['subject'],
                jql_query=jql_query
            )
        else:
            print("\n[Step 8] Email not configured. Skipping email delivery.")

        print("\n" + "="*80)
        print("✓ Analysis Complete!")
        print("="*80)
        print("\nGenerated Files in reports/ directory:")
        print("  • reports/jira_table.csv - Complete JIRA data")
        print("  • reports/jira_status_report.csv - Status report (Success/Failed)")
        print("  • reports/jira_status_report.html - Interactive HTML report")
        if detailed_report:
            print("  • Report and Log Files columns included (--detailed-report mode)")
        print()


def main():
    """Main execution function."""
    import argparse
    parser = argparse.ArgumentParser(description='JIRA Table Analyzer')
    parser.add_argument('--detailed-report', action='store_true',
                        help='Fetch remote links per issue and add Report and Log Files columns')
    args = parser.parse_args()

    # Load environment variables from .env file
    load_dotenv()

    # Get credentials from environment variables
    JIRA_URL = os.getenv('JIRA_URL', 'https://jira-sd.mc1.oracleiaas.com')
    JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')

    # Validate credentials
    if not JIRA_API_TOKEN:
        print("="*80)
        print("✗ ERROR: Missing JIRA credentials")
        print("="*80)
        print("Please create a .env file in the project root with the following:")
        print()
        print("JIRA_URL=https://jira-sd.mc1.oracleiaas.com")
        print("JIRA_API_TOKEN=your_api_token_here")
        print("JQL_QUERY=your_jql_query_here  # Optional, defaults to ExaInfra patching failures")
        print("MAX_RESULTS=100  # Optional, defaults to 100")
        print()
        print("See README.md for detailed setup instructions.")
        print("="*80)
        return

    # JQL Query from environment variable
    JQL_QUERY = os.getenv('JQL_QUERY', """
    text ~ metricsV2.EXADATA.dbaas.patchCloudExaInfra.APPLY.WORKER.Failure
    AND labels in (oneview_triagex_started,oneview_triagex_success,oneview_triagex_failed)
    AND created >= -3d
    ORDER BY created DESC
    """).strip()

    # Maximum number of results to fetch
    MAX_RESULTS = int(os.getenv('MAX_RESULTS', 100))

    # Email configuration (optional)
    email_config = None
    EMAIL_SMTP_SERVER = os.getenv('EMAIL_SMTP_SERVER')
    EMAIL_FROM = os.getenv('EMAIL_FROM')
    EMAIL_TO = os.getenv('EMAIL_TO')
    EMAIL_SUBJECT = os.getenv('EMAIL_SUBJECT', 'JIRA Status Report')

    # Append date range to email subject if JQL contains a relative created filter (e.g., created >= -3d)
    created_match = re.search(r'created\s*>=\s*-(\d+)d', JQL_QUERY)
    if created_match:
        days_back = int(created_match.group(1))
        today = datetime.now()
        from_date = today - timedelta(days=days_back)
        EMAIL_SUBJECT = f"{EMAIL_SUBJECT} from {from_date.strftime('%b %d, %Y')} to {today.strftime('%b %d, %Y')}"

    if EMAIL_SMTP_SERVER and EMAIL_FROM and EMAIL_TO:
        email_config = {
            'smtp_server': EMAIL_SMTP_SERVER,
            'from': EMAIL_FROM,
            'to': EMAIL_TO,
            'subject': EMAIL_SUBJECT
        }

    print("="*80)
    print("JIRA TABLE ANALYZER")
    print("="*80)
    print(f"JIRA Instance: {JIRA_URL}")
    print(f"Query Filter: {JQL_QUERY.strip()}")
    print(f"Max Results: {MAX_RESULTS}")
    print(f"Email: {'Configured' if email_config else 'Not configured'}")
    print("="*80)

    try:
        # Create analyzer with credentials from .env
        analyzer = JiraTableAnalyzer(JIRA_URL, JIRA_API_TOKEN)

        # Run the analysis
        analyzer.run(JQL_QUERY, MAX_RESULTS, email_config, detailed_report=args.detailed_report)

    except KeyboardInterrupt:
        print("\n\n✗ Operation cancelled by user.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
