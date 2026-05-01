# Code Review — TriageX JIRA Dashboard
**Date:** 2026-04-30
**Branch:** main
**Reviewer:** Claude Code (automated)

---

## Stats

- Files Modified: 1 (`.agents/plans/triagex-jira-dashboard.md` — docs only)
- Files Added: 5
  - `application/backend/app.py`
  - `application/backend/jira_analyzer.py`
  - `application/backend/requirements.txt`
  - `application/frontend/templates/dashboard.html`
  - `application/README.md`
  - `application/.env.template`
- Files Deleted: 0
- New lines: ~855 (dashboard.html) + ~399 (app.py) + ~121 (jira_analyzer.py) + ~35 (.env.template) + ~160 (README.md)

---

## Issues Found

---

```
severity: high
file: application/frontend/templates/dashboard.html
line: 709
issue: XSS via javascript: URL in report_link href
detail: renderRow() places issue.report_link directly into a href attribute after only calling
        escHtml(), which escapes HTML entities (&, <, >, ") but does NOT block javascript: URLs.
        If a JIRA remote link title matches 'VoxioTriageX - Triage Report' and its URL is set
        to "javascript:fetch('/api/send-email',{method:'POST',body:JSON.stringify({...})})",
        clicking "Report" executes arbitrary JavaScript in the user's browser. Any JIRA user
        who can create remote links on tracked tickets can exploit this.
suggestion: Validate the URL protocol before rendering. Add a helper:
        function safeUrl(u) { return /^https?:\/\//i.test(u) ? u : '#'; }
        Then use: href="${safeUrl(escHtml(issue.report_link))}"
        Mirror the same fix in _generate_email_html() in app.py (line 132), where report_url
        is also interpolated directly into an href without protocol validation.
```

---

```
severity: high
file: application/backend/app.py
line: 355
issue: Email recipient injection — API accepts arbitrary addresses, bypassing UI allowlist
detail: The /api/send-email endpoint reads recipients directly from the POST body:
        recipients = [r.strip() for r in (body.get('recipients') or []) if r.strip()]
        There is no check that the supplied addresses belong to DEFAULT_EMAIL_RECIPIENTS.
        Because the server binds to 0.0.0.0, any host on the network can POST to
        /api/send-email with arbitrary recipient addresses, turning the server into an
        open relay to anyone reachable by the internal SMTP server.
suggestion: Validate recipients against the allowed pool before sending:
        allowed = set(DEFAULT_EMAIL_RECIPIENTS)
        recipients = [r for r in recipients if r in allowed]
        if not recipients:
            return jsonify({'error': 'No valid recipients.'}), 400
```

---

```
severity: medium
file: application/backend/app.py
line: 38
issue: rstrip('AND') strips individual characters, not the substring "AND"
detail: str.rstrip(chars) removes any trailing character found in the chars argument —
        it treats the argument as a character set, not a substring.
        jql.strip().rstrip('AND') strips any trailing combination of 'A', 'N', 'D' chars.
        Example: strip_date_conditions("project = DEMAND") → after regexes match nothing →
        rstrip('AND') strips trailing 'D','N','A' → "project = DEM".
        Any JQL that ends with characters in {A, N, D} after date/ORDER BY removal is silently
        corrupted before the new date range is appended.
suggestion: Replace the character-based rstrip with a regex:
        import re
        jql = re.sub(r'\s+(?:AND|OR)\s*$', '', jql, flags=re.IGNORECASE).strip()
```

---

```
severity: medium
file: application/backend/app.py
line: 289
issue: JQL injection via unvalidated from_date / to_date parameters
detail: from_date and to_date are user-supplied strings inserted directly into the JQL:
        jql = f'{base} AND created >= "{from_date}" AND created <= "{to_date}" ...'
        The only check is that both are non-empty (line 277). No format validation is
        performed server-side. A caller can set from_date to:
            2024-01-01" OR labels = "arbitrary
        producing: ... AND created >= "2024-01-01" OR labels = "arbitrary" AND created <= ...
        This allows arbitrary JQL injection, potentially leaking issues outside the
        intended project scope.
suggestion: Validate date format before interpolation:
        import re
        DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        if from_date and not DATE_RE.match(from_date):
            return jsonify({'error': 'Invalid from_date format (expected YYYY-MM-DD).'}), 400
        if to_date and not DATE_RE.match(to_date):
            return jsonify({'error': 'Invalid to_date format (expected YYYY-MM-DD).'}), 400
```

---

```
severity: medium
file: application/backend/app.py
line: 132
issue: Unescaped report_url from JIRA remote links inserted into email HTML href
detail: In _generate_email_html(), report_url is taken from row.get('Report Link', '') —
        which comes from JIRA remote link objects fetched by fetch_remote_links() — and
        embedded raw into an <a href="..."> tag without sanitisation:
            report_cell = f'<td ...><a href="{report_url}" ...>Report</a></td>'
        A crafted JIRA remote link URL containing a double-quote could break out of the
        attribute and inject arbitrary HTML into the email body. Even without breakout, a
        javascript: URL would execute in email clients that render HTML and allow JS (rare
        but possible in some enterprise clients).
suggestion: Escape the URL for HTML context and restrict to http(s):
        safe_url = report_url if re.match(r'^https?://', report_url) else '#'
        import html as _html
        report_cell = f'<td ...><a href="{_html.escape(safe_url)}" ...>Report</a></td>'
```

---

```
severity: low
file: application/backend/app.py
line: 342
issue: Internal exception message returned verbatim to API client
detail: except Exception as exc: ... return jsonify({'error': str(exc)}), 500
        str(exc) can expose internal details: JIRA server addresses, auth failure messages,
        file paths from stack frames, or library version strings. For an internal tool this
        is low risk, but it makes it easier for an attacker who probes the API to enumerate
        the environment.
suggestion: Log the full exception server-side (already done with traceback.print_exc())
        and return a generic message to the client:
        return jsonify({'error': 'Analysis failed. Check server logs for details.'}), 500
        Expose exc details only when running in DEBUG mode.
```

---

```
severity: low
file: application/backend/jira_analyzer.py
line: 92
issue: fetch_issues_from_jira silently returns empty DataFrame on JIRA errors
detail: The except block prints the error and returns pd.DataFrame(). The caller in app.py
        (line 298-303) treats an empty DataFrame the same as "zero results", so a JIRA
        connection failure, an auth error, or a malformed JQL error all produce the identical
        response: {"summary": {"total": 0, ...}}. The user sees "no results" with no indication
        that the query actually failed.
suggestion: Re-raise the exception so the caller's except block (app.py line 342) can
        return an HTTP 500 with the error message. Remove the try/except in this method, or
        raise a domain-specific exception class so the API layer can distinguish "empty results"
        from "query error".
```

---

```
severity: low
file: application/backend/jira_analyzer.py
line: 39
issue: fetch_remote_links silently swallows per-ticket errors during enrichment
detail: If fetching remote links fails for one ticket (e.g., network blip, permission error),
        the exception is caught, a warning is printed, and the ticket gets empty report/log
        fields with no indication in the API response that enrichment was partial.
suggestion: Acceptable as-is for resilience, but surface the partial-failure count in the
        API response. In enrich_with_remote_links(), track failures and include them in the
        returned DataFrame or pass a warning back to app.py to include in the JSON response.
```

---

```
severity: low
file: application/frontend/templates/dashboard.html
line: 464
issue: email_from and email_smtp template variables rendered without explicit Jinja2 escaping
detail: {{ email_from }} and {{ email_smtp }} are rendered without the | e escape filter:
            From: <code>{{ email_from }}</code> via <code>{{ email_smtp }}</code>
        Flask auto-escapes in .html templates via Jinja2's autoescape, so in practice this is
        safe. However, it is inconsistent with {{ default_jql | e }} (line 406) and
        {{ default_email_subject | tojson }} (line 549) which both apply explicit escaping,
        making the intent ambiguous and the code harder to audit.
suggestion: Add | e for consistency and to make the escaping intent explicit:
            From: <code>{{ email_from | e }}</code> via <code>{{ email_smtp | e }}</code>
```

---

## Summary

| Severity | Count |
|----------|-------|
| High     | 2     |
| Medium   | 3     |
| Low      | 4     |

The two high-severity issues should be fixed before this tool is used on the corporate network:
1. The `javascript:` URL XSS in the dashboard's Report link column.
2. The email relay open to arbitrary recipients via direct API calls.

The medium-severity `rstrip('AND')` bug is a silent correctness issue that could corrupt JQL in
edge cases but is unlikely to manifest with typical JIRA project names. The JQL injection via date
fields is a real vector but is mitigated in practice by the browser's `<input type="date">` UI.
