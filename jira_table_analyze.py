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
                report_data.append({
                    "JIRA ID": key,
                    "Status": status,
                    "Date": created_date,
                    "Link": link
                })

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
            print(f"  Total Issues: {len(status_df)}")
            print(f"  Success: {len(status_df[status_df['Status'] == 'Success'])}")
            print(f"  Failed: {len(status_df[status_df['Status'] == 'Failed'])}")
        else:
            print("No matching issues found with success/failed labels.")
        print("=" * 100 + "\n")

    def save_status_report_to_csv(self, status_df: pd.DataFrame, output_path: str) -> str:
        """Save status report to CSV."""
        status_df.to_csv(output_path, index=False)
        print(f"✓ Saved status report to {output_path}")
        return output_path

    def create_html_report(self, status_df: pd.DataFrame, output_path: str) -> str:
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

            # Generate table rows
            rows_html = ""
            for _, row in status_df.iterrows():
                status_class = "status-success" if row['Status'] == 'Success' else "status-failed"
                status_text = "SUCCESS" if row['Status'] == 'Success' else "FAILED"
                rows_html += f"""
                <tr>
                    <td>
                        <a href="{row['Link']}" target="_blank" class="jira-link">
                            {row['JIRA ID']}
                        </a>
                    </td>
                    <td>
                        <span class="status-badge {status_class}">
                            {status_text}
                        </span>
                    </td>
                    <td>
                        {row['Date']}
                    </td>
                </tr>
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
                </style>
            </head>
            <body>
                <h1>JIRA Status Report</h1>

                <div class="summary">
                    <h3>Summary</h3>
                    <p><strong>Total Issues:</strong> {total}</p>
                    <p><strong>Success:</strong> {success}</p>
                    <p><strong>Failed:</strong> {failed}</p>

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

    def run(self, jql_query: str, max_results: int = 100):
        """
        Execute the complete workflow.

        Args:
            jql_query: JQL filter string
            max_results: Maximum number of results to fetch
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
        self.create_html_report(self.status_df, 'reports/jira_status_report.html')

        # 7. Print final status report
        print("\n[Step 7] Displaying final status report...")
        self.print_status_report(self.status_df)

        print("\n" + "="*80)
        print("✓ Analysis Complete!")
        print("="*80)
        print("\nGenerated Files in reports/ directory:")
        print("  • reports/jira_table.csv - Complete JIRA data")
        print("  • reports/jira_status_report.csv - Status report (Success/Failed)")
        print("  • reports/jira_status_report.html - Interactive HTML report")
        print()


def main():
    """Main execution function."""

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
        print()
        print("See README.md for detailed setup instructions.")
        print("="*80)
        return

    # JQL Query - Last 1 day of ExaInfra patching failures
    JQL_QUERY = """
    text ~ metricsV2.EXADATA.dbaas.patchCloudExaInfra.APPLY.WORKER.Failure
    AND labels in (oneview_triagex_started,oneview_triagex_success,oneview_triagex_failed)
    AND created >= -3d
    ORDER BY created DESC
    """

    # Maximum number of results to fetch
    MAX_RESULTS = int(os.getenv('MAX_RESULTS', 100))

    print("="*80)
    print("JIRA TABLE ANALYZER")
    print("="*80)
    print(f"JIRA Instance: {JIRA_URL}")
    print(f"Query Filter: {JQL_QUERY.strip()}")
    print(f"Max Results: {MAX_RESULTS}")
    print("="*80)

    try:
        # Create analyzer with credentials from .env
        analyzer = JiraTableAnalyzer(JIRA_URL, JIRA_API_TOKEN)

        # Run the analysis
        analyzer.run(JQL_QUERY, MAX_RESULTS)

    except KeyboardInterrupt:
        print("\n\n✗ Operation cancelled by user.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
