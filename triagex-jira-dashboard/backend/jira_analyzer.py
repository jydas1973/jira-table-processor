#!/usr/bin/env python3
import pandas as pd
from typing import Dict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from jira import JIRA

# Remote-link fetch tuning
MAX_LINK_WORKERS  = 10      # concurrent threads when enriching tickets
CACHE_TTL_SECONDS = 3600    # 1 hour

# Module-level cache: jira_key → {'data': dict, 'ts': datetime}
_LINK_CACHE: dict = {}


class JiraAnalyzer:
    def __init__(self, jira_url: str, api_token: str):
        self.jira_url = jira_url
        self.jira = None
        self.df = pd.DataFrame()
        self.status_df = pd.DataFrame()
        self._connect(api_token)

    def _connect(self, api_token: str):
        try:
            print(f"Connecting to JIRA at {self.jira_url}...")
            jira_options = {'server': self.jira_url}
            self.jira = JIRA(options=jira_options, token_auth=api_token)
            print("✓ Successfully connected to JIRA")
        except Exception as e:
            print(f"✗ Failed to connect to JIRA: {e}")
            raise

    def fetch_remote_links(self, key: str) -> Dict:
        # Return cached result if still fresh
        cached = _LINK_CACHE.get(key)
        if cached and (datetime.now() - cached['ts']).total_seconds() < CACHE_TTL_SECONDS:
            return cached['data']

        result = {'report_url': None, 'log_files': [], 'error': False}
        try:
            remote_links = self.jira.remote_links(key)
            for rl in remote_links:
                obj = rl.object
                title = getattr(obj, 'title', '') or ''
                url   = getattr(obj, 'url',   '') or ''
                if title == 'VoxioTriageX - Triage Report':
                    result['report_url'] = url
                elif title.startswith('TriageX - Log '):
                    result['log_files'].append(title[len('TriageX - Log '):])
        except Exception as e:
            print(f"  ⚠ Could not fetch remote links for {key}: {e}")
            result['error'] = True

        # Only cache successful fetches so errors are always retried
        if not result['error']:
            _LINK_CACHE[key] = {'data': result, 'ts': datetime.now()}
        return result

    def enrich_with_remote_links(self, df: pd.DataFrame) -> pd.DataFrame:
        keys = list(df['Key'])
        cache_hits = sum(1 for k in keys if k in _LINK_CACHE and
                         (datetime.now() - _LINK_CACHE[k]['ts']).total_seconds() < CACHE_TTL_SECONDS)
        print(f"\n[Detailed Report] Fetching remote links for {len(keys)} issues "
              f"({cache_hits} cached, {MAX_LINK_WORKERS} parallel workers)...")

        link_results: dict = {}
        failures = 0

        with ThreadPoolExecutor(max_workers=MAX_LINK_WORKERS) as pool:
            future_to_key = {pool.submit(self.fetch_remote_links, key): key for key in keys}
            for future in as_completed(future_to_key):
                key   = future_to_key[future]
                links = future.result()
                if links['error']:
                    failures += 1
                link_results[key] = links

        df = df.copy()
        df['Report Link'] = [link_results[k]['report_url'] or '' for k in keys]
        df['Log Files']   = [', '.join(link_results[k]['log_files']) for k in keys]
        self.enrichment_failures = failures
        print(f"  ✓ Done — {len(keys) - failures}/{len(keys)} succeeded, {failures} failed")
        return df

    def fetch_issues_from_jira(self, jql_query: str, max_results: int = 100) -> pd.DataFrame:
        print(f"\nExecuting JQL query:")
        print(f"  {jql_query}")
        print(f"  Max results: {max_results}\n")
        try:
            issues = self.jira.search_issues(
                jql_query,
                maxResults=max_results,
                fields='key,summary,assignee,reporter,priority,status,resolution,created,updated,duedate,labels'
            )
            print(f"✓ Found {len(issues)} issues")
            data = []
            for issue in issues:
                assignee = issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned'
                reporter = issue.fields.reporter.displayName if issue.fields.reporter else 'Unknown'
                priority = issue.fields.priority.name if issue.fields.priority else ''
                labels = ' '.join(issue.fields.labels) if issue.fields.labels else ''
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
            raise

    def process_labels_and_create_status_report(self, df: pd.DataFrame) -> pd.DataFrame:
        report_data = []
        for index, row in df.iterrows():
            key = row['Key']
            labels = str(row['Labels']).lower() if pd.notna(row['Labels']) else ''
            created_date = row['Created'] if pd.notna(row['Created']) else ''
            link = f"{self.jira_url}/browse/{key}"
            status = None
            if 'oneview_triagex_failed' in labels:
                status = "Failed"
            elif 'oneview_triagex_success' in labels:
                status = "Success"
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
