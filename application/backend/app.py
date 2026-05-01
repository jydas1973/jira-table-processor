#!/usr/bin/env python3
import sys
import os
import re
import html as _html
import argparse
import socket
import traceback
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import pandas as pd

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

app = Flask(__name__, template_folder='../frontend/templates')

JIRA_URL       = os.getenv('JIRA_URL', 'https://jira-sd.mc1.oracleiaas.com')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN', '')
DEFAULT_JQL    = os.getenv('JQL_QUERY', '').strip().strip("'\"")

EMAIL_SMTP_SERVER        = os.getenv('EMAIL_SMTP_SERVER', '')
EMAIL_FROM               = os.getenv('EMAIL_FROM', '')
EMAIL_TO_RAW             = os.getenv('EMAIL_TO', '')
DEFAULT_EMAIL_RECIPIENTS = [e.strip() for e in EMAIL_TO_RAW.split(',') if e.strip()]
DEFAULT_EMAIL_SUBJECT    = os.getenv('EMAIL_SUBJECT', 'TriageX JIRA Analysis Report')

_last_status_df: pd.DataFrame = pd.DataFrame()


def strip_date_conditions(jql: str) -> str:
    jql = re.sub(r'\s+AND\s+created\s*>=\s*["\']?[-\w]+["\']?', '', jql, flags=re.IGNORECASE)
    jql = re.sub(r'\s+AND\s+created\s*<=\s*["\']?[-\w]+["\']?', '', jql, flags=re.IGNORECASE)
    jql = re.sub(r'created\s*>=\s*["\']?[-\w]+["\']?\s+AND\s+', '', jql, flags=re.IGNORECASE)
    jql = re.sub(r'created\s*<=\s*["\']?[-\w]+["\']?\s+AND\s+', '', jql, flags=re.IGNORECASE)
    jql = re.sub(r'\s+ORDER\s+BY\s+.*$', '', jql, flags=re.IGNORECASE)
    return re.sub(r'\s+(?:AND|OR)\s*$', '', jql, flags=re.IGNORECASE).strip()


def validate_jql(jql: str):
    if not jql or not jql.strip():
        return "JQL query cannot be empty."
    stripped = jql.strip()
    keywords = ['project', 'labels', 'text', 'issuetype', 'assignee', 'reporter', 'status']
    if not any(k in stripped.lower() for k in keywords):
        return "JQL query appears invalid — it must contain at least one field filter (e.g. project, labels)."
    return None


def compute_weekly_stats(status_df: pd.DataFrame,
                         from_date: str = '', to_date: str = '') -> list:
    if status_df.empty:
        return []
    df = status_df.copy()
    df['_date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['_date'])
    if df.empty:
        return []

    if from_date and to_date:
        # Fixed 7-day buckets anchored to from_date so the chart always shows
        # evenly spaced intervals regardless of where tickets fall.
        range_start = datetime.strptime(from_date, '%Y-%m-%d')
        range_end   = datetime.strptime(to_date,   '%Y-%m-%d')
        weekly = []
        bucket_start = range_start
        while bucket_start <= range_end:
            bucket_end     = min(bucket_start + timedelta(days=6), range_end)
            mask           = ((df['_date'].dt.date >= bucket_start.date()) &
                              (df['_date'].dt.date <= bucket_end.date()))
            group          = df[mask]
            total          = len(group)
            success        = int((group['Status'] == 'Success').sum()) if total > 0 else 0
            rate           = round(success / total * 100, 1) if total > 0 else 0.0
            label          = f'{bucket_start.strftime("%b %d")}–{bucket_end.strftime("%b %d")}'
            weekly.append({
                'label'       : label,
                'success_rate': rate,
                'total'       : total,
                'success'     : success,
                'failed'      : total - success,
            })
            bucket_start += timedelta(days=7)
        return weekly

    # No explicit date range — fall back to ISO calendar weeks.
    iso = df['_date'].dt.isocalendar()
    df['_year'] = iso.year.astype(int)
    df['_week'] = iso.week.astype(int)
    weekly = []
    for (year, week), group in df.groupby(['_year', '_week']):
        total   = len(group)
        success = int((group['Status'] == 'Success').sum())
        rate    = round(success / total * 100, 1) if total > 0 else 0.0
        try:
            week_start = datetime.strptime(f'{year}-W{week:02d}-1', '%G-W%V-%u')
            week_end   = week_start + timedelta(days=6)
            label      = f'W{week} ({week_start.strftime("%b %d")}–{week_end.strftime("%b %d")})'
        except ValueError:
            label = f'Week {week}'
        weekly.append({
            'label'       : label,
            'iso_year'    : int(year),
            'iso_week'    : int(week),
            'success_rate': rate,
            'total'       : total,
            'success'     : success,
            'failed'      : total - success,
        })
    return sorted(weekly, key=lambda x: (x['iso_year'], x['iso_week']))


def _generate_email_html(status_df: pd.DataFrame) -> str:
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
                safe_url = report_url if re.match(r'^https?://', report_url) else '#'
                escaped_url = _html.escape(safe_url)
                report_cell = (f'<td style="padding:12px 16px;border-bottom:1px solid #f4f5f7;">'
                               f'<a href="{escaped_url}" target="_blank" '
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


def _send_via_smtp(html_body: str, recipients: list, subject: str):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart()
    msg['From']    = EMAIL_FROM
    msg['To']      = ', '.join(recipients)
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    with smtplib.SMTP(EMAIL_SMTP_SERVER, 25) as server:
        server.sendmail(EMAIL_FROM, recipients, msg.as_string())
    print(f'[TriageX] Email sent to {len(recipients)} recipient(s) via {EMAIL_SMTP_SERVER}')


@app.route('/')
def index():
    return render_template('dashboard.html',
        jira_url=JIRA_URL,
        default_jql=DEFAULT_JQL,
        has_token=bool(JIRA_API_TOKEN),
        email_recipients=DEFAULT_EMAIL_RECIPIENTS,
        email_from=EMAIL_FROM,
        email_smtp=EMAIL_SMTP_SERVER,
        default_email_subject=DEFAULT_EMAIL_SUBJECT,
    )


@app.route('/api/analyze', methods=['POST'])
def analyze():
    global _last_status_df

    body = request.get_json(force=True) or {}

    from_date      = (body.get('from_date') or '').strip()
    to_date        = (body.get('to_date') or '').strip()
    jql_input      = (body.get('jql') or DEFAULT_JQL).strip().strip("'\"")
    include_detail = bool(body.get('include_detail', False))
    try:
        max_results = min(max(int(body.get('max_results', 500)), 1), 1000)
    except (ValueError, TypeError):
        max_results = 500

    if bool(from_date) != bool(to_date):
        return jsonify({'error': 'Please fill both From and To dates, or leave both empty.'}), 400

    _DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    if from_date and not _DATE_RE.match(from_date):
        return jsonify({'error': 'Invalid from_date format (expected YYYY-MM-DD).'}), 400
    if to_date and not _DATE_RE.match(to_date):
        return jsonify({'error': 'Invalid to_date format (expected YYYY-MM-DD).'}), 400

    err = validate_jql(jql_input)
    if err:
        return jsonify({'error': err}), 400

    if not JIRA_API_TOKEN:
        return jsonify({'error': 'JIRA_API_TOKEN is not configured. Add it to application/.env'}), 500

    if from_date and to_date:
        base = strip_date_conditions(jql_input)
        jql = f'{base} AND created >= "{from_date}" AND created <= "{to_date}" ORDER BY created DESC'
    else:
        jql = jql_input
        if 'ORDER BY' not in jql.upper():
            jql += ' ORDER BY created DESC'

    try:
        from jira_analyzer import JiraAnalyzer
        analyzer = JiraAnalyzer(JIRA_URL, JIRA_API_TOKEN)
        raw_df = analyzer.fetch_issues_from_jira(jql, max_results)

        EMPTY = {'summary': {'total': 0, 'success': 0, 'failed': 0, 'success_pct': 0.0},
                 'issues': [], 'weekly_data': [], 'jql': jql}

        if raw_df.empty:
            return jsonify(EMPTY)

        enrichment_warning = None
        if include_detail:
            raw_df = analyzer.enrich_with_remote_links(raw_df)
            failures = getattr(analyzer, 'enrichment_failures', 0)
            if failures:
                enrichment_warning = f'Remote link fetch failed for {failures} ticket(s). Those tickets show no Report/Log data.'

        status_df = analyzer.process_labels_and_create_status_report(raw_df)

        if status_df.empty:
            return jsonify(EMPTY)

        _last_status_df = status_df.copy()

        total         = len(status_df)
        success_count = int((status_df['Status'] == 'Success').sum())
        failed_count  = total - success_count
        success_pct   = round(success_count / total * 100, 1) if total > 0 else 0.0

        issues = []
        for _, row in status_df.iterrows():
            log_raw   = str(row.get('Log Files', '') or '')
            log_files = [f.strip() for f in log_raw.split(',') if f.strip()] if log_raw else []
            issues.append({
                'jira_id'    : row['JIRA ID'],
                'status'     : row['Status'],
                'date'       : row['Date'],
                'link'       : row['Link'],
                'report_link': str(row.get('Report Link', '') or ''),
                'log_files'  : log_files,
            })

        response = {
            'summary'    : {'total': total, 'success': success_count,
                            'failed': failed_count, 'success_pct': success_pct},
            'issues'     : issues,
            'weekly_data': compute_weekly_stats(status_df, from_date, to_date),
            'jql'        : jql,
        }
        if enrichment_warning:
            response['warning'] = enrichment_warning
        return jsonify(response)

    except Exception:
        traceback.print_exc()
        return jsonify({'error': 'Analysis failed. Check server logs for details.'}), 500


@app.route('/api/send-email', methods=['POST'])
def send_email():
    global _last_status_df

    if _last_status_df.empty:
        return jsonify({'error': 'No analysis results available. Please run Analyze first.'}), 400

    body       = request.get_json(force=True) or {}
    allowed    = set(DEFAULT_EMAIL_RECIPIENTS)
    recipients = [r.strip() for r in (body.get('recipients') or []) if r.strip() and r.strip() in allowed]
    subject    = (body.get('subject') or DEFAULT_EMAIL_SUBJECT).strip()

    if not recipients:
        return jsonify({'error': 'No valid recipients. Only addresses from the configured EMAIL_TO list are allowed.'}), 400

    if not EMAIL_SMTP_SERVER:
        return jsonify({'error': 'EMAIL_SMTP_SERVER is not configured in .env'}), 500

    if not EMAIL_FROM:
        return jsonify({'error': 'EMAIL_FROM is not configured in .env'}), 500

    df_to_send = _last_status_df.head(50)

    try:
        html_body = _generate_email_html(df_to_send)
        _send_via_smtp(html_body, recipients, subject)
        return jsonify({'sent': len(recipients), 'recipients': recipients})
    except Exception as exc:
        traceback.print_exc()
        return jsonify({'error': str(exc)}), 500


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) != 0


def main():
    parser = argparse.ArgumentParser(description='TriageX JIRA Dashboard')
    parser.add_argument('--open', action='store_true',
                        help='Open the dashboard in your default browser after the server starts')
    parser.add_argument('--port', type=int,
                        default=int(os.getenv('DASHBOARD_PORT', 5000)),
                        help='Port to run the server on (default: 5000)')
    args = parser.parse_args()

    if not JIRA_API_TOKEN:
        print('[TriageX] ERROR: JIRA_API_TOKEN is not configured.')
        print('[TriageX]        Add JIRA_API_TOKEN=<your-token> to application/.env and retry.')
        sys.exit(1)

    if not _port_is_free(args.port):
        print(f'[TriageX] ERROR: Port {args.port} is already in use.')
        print(f'[TriageX]        Free it with: lsof -ti:{args.port} | xargs kill')
        sys.exit(1)

    if args.open:
        import threading
        import webbrowser
        threading.Timer(1.2, lambda: webbrowser.open(f'http://localhost:{args.port}')).start()

    print(f'[TriageX] Dashboard → http://localhost:{args.port}')
    print(f'[TriageX] JIRA      → {JIRA_URL}')
    print(f'[TriageX] Token     → configured ✓')
    app.run(host='0.0.0.0', port=args.port, debug=False)


if __name__ == '__main__':
    main()
