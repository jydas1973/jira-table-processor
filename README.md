# JIRA Table Analyzer - Setup Guide

A Python tool that queries JIRA directly using JQL filters and generates comprehensive status reports based on label analysis. No image scanning required - data is fetched directly from the JIRA API.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Output Files](#output-files)
- [Troubleshooting](#troubleshooting)

---

## Overview

This tool connects to your JIRA instance, executes a JQL (JIRA Query Language) query, retrieves issue data, and analyzes labels to generate status reports in multiple formats (CSV, HTML).

**Key Features:**
- Direct JIRA API integration (no image scanning)
- Configurable JQL queries
- Automated label analysis for success/failed status
- Multiple output formats (CSV, HTML with clickable links)
- Secure credential management via .env file

---

## Prerequisites

### 1. Python Version
- **Python 3.8 or higher** is required
- Verify your version:
  ```bash
  python --version
  ```

### 2. Required Python Packages
The following packages are required and will be installed via `requirements.txt`:
- **pandas** (>=2.0.0) - Data manipulation and analysis
- **jira** (>=3.5.0) - JIRA REST API client
- **python-dotenv** (>=1.0.0) - Environment variable management from .env files

Optional packages (included for other scripts in this project):
- **Pillow**, **opencv-python**, **pytesseract** - For image-based JIRA table extraction (not needed for jira_table_analyze.py)
- **openpyxl** - Excel file support
- **tabulate** - Table formatting

### 3. JIRA Account & Access
- Active JIRA account with read access to the target instance
- JIRA instance URL (e.g., `https://jira-sd.mc1.oracleiaas.com`)
- Valid credentials (username and API token)

### 3. JIRA API Token
You need to generate a JIRA API token:

#### For Atlassian Cloud JIRA:
1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **Create API token**
3. Give it a label (e.g., "JIRA Table Analyzer")
4. Click **Create**
5. **Copy the token immediately** (you won't be able to see it again)

#### For Oracle Internal JIRA or Self-Hosted:
- Contact your JIRA administrator for API token generation instructions
- May require different authentication methods (consult your IT team)

---

## Installation

### Step 1: Clone or Download the Repository
```bash
cd /path/to/your/project
```

### Step 2: Create a Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

**All required packages are listed in `requirements.txt`:**
- Core packages for `jira_table_analyze.py`: `jira`, `pandas`, `python-dotenv`
- Additional packages for other scripts: `Pillow`, `opencv-python`, `pytesseract`, `openpyxl`, `tabulate`

**Note:** If you only plan to use `jira_table_analyze.py` (API-based), you only need to install:
```bash
pip install pandas jira python-dotenv
```

However, installing all requirements ensures compatibility with other scripts in this repository.

---

## Configuration

### Step 1: Create .env File

Copy the template file to create your configuration:

```bash
# On Windows:
copy .env.template .env

# On Linux/Mac:
cp .env.template .env
```

### Step 2: Edit .env File

Open `.env` in a text editor and fill in your credentials:

```bash
# JIRA Instance URL (update if different)
JIRA_URL=https://jira-sd.mc1.oracleiaas.com

# Your JIRA username/email
JIRA_USERNAME=your.email@oracle.com

# Your JIRA API token (generated from previous step)
JIRA_API_TOKEN=ATBBt3xY8r9K2mN5pQsT1uVwXyZaBcDeFgHiJkLm

# Optional: Maximum number of results (default: 100)
MAX_RESULTS=100
```

**Important Security Notes:**
- ✅ The `.env` file is listed in `.gitignore` - it will NOT be committed to version control
- ❌ NEVER share your `.env` file or commit it to Git
- ❌ NEVER hardcode credentials directly in Python scripts
- ✅ Treat your API token like a password

### Step 3: Verify Configuration

Check that your `.env` file is properly formatted:
```bash
# On Windows:
type .env

# On Linux/Mac:
cat .env
```

---

## Usage

### Running the Program Standalone

This program (`jira_table_analyze.py`) can be run completely standalone - it only requires:
1. Python 3.8+
2. Three Python packages: `pandas`, `jira`, `python-dotenv`
3. A `.env` file with your JIRA credentials

**Quick Start (Standalone):**

```bash
# 1. Navigate to the project directory
cd C:\Users\YourName\path\to\generate_report_from_jira_analysis

# 2. Install only the required packages
pip install pandas jira python-dotenv

# 3. Create .env file with your credentials
# (Copy .env.template to .env and fill in your details)

# 4. Run the program
python jira_table_analyze.py

# 5. Check the results in the reports/ directory
dir reports  # Windows
ls reports   # Linux/Mac
```

### Basic Execution

Run the script with default settings:
```bash
python jira_table_analyze.py
```

**Expected Output:**
```
================================================================================
JIRA TABLE ANALYZER
================================================================================
JIRA Instance: https://jira-sd.mc1.oracleiaas.com
Query Filter: text ~ metricsV2.EXADATA.dbaas.patchCloudExaInfra.APPLY.WORKER.Failure...
Max Results: 100
================================================================================
Connecting to JIRA at https://jira-sd.mc1.oracleiaas.com...
✓ Successfully connected to JIRA

[Setup] Creating reports/ directory...
✓ reports/ directory ready

[Step 1] Fetching issues from JIRA...
✓ Found X issues

[Step 2] Saving original data to CSV...
✓ Saved table to reports/jira_table.csv

[Step 3] Displaying original table...
[... table output ...]

[Step 4] Processing labels and creating status report...

[Step 5] Saving status report to CSV...
✓ Saved status report to reports/jira_status_report.csv

[Step 6] Creating HTML report with hyperlinks...
✓ Saved HTML report to reports/jira_status_report.html

[Step 7] Displaying final status report...
[... status report ...]

================================================================================
✓ Analysis Complete!
================================================================================

Generated Files in reports/ directory:
  • reports/jira_table.csv - Complete JIRA data
  • reports/jira_status_report.csv - Status report (Success/Failed)
  • reports/jira_status_report.html - Interactive HTML report
```

### What Happens When You Run It:

1. **Loads credentials** from `.env` file
2. **Connects to JIRA** using your credentials
3. **Prepares output directory:**
   - Creates `reports/` directory if it doesn't exist
   - Cleans any previous files from `reports/` directory
4. **Executes JQL query:**
   ```sql
   text ~ metricsV2.EXADATA.dbaas.patchCloudExaInfra.APPLY.WORKER.Failure
   AND labels in (oneview_triagex_started,oneview_triagex_success,oneview_triagex_failed)
   AND created >= -1d
   ORDER BY created DESC
   ```
5. **Fetches issue data** (Key, Summary, Assignee, Labels, etc.)
6. **Analyzes labels** for success/failed status:
   - `oneview_triagex_success` → Status: **Success**
   - `oneview_triagex_failed` → Status: **Failed**
7. **Generates reports** in multiple formats and saves them to `reports/` directory

### Customizing the JQL Query

To modify the query, edit the `JQL_QUERY` variable in `jira_table_analyze.py`:

```python
# Line ~265 in jira_table_analyze.py
JQL_QUERY = """
    text ~ metricsV2.EXADATA.dbaas.patchCloudExaInfra.APPLY.WORKER.Failure
    AND labels in (oneview_triagex_started,oneview_triagex_success,oneview_triagex_failed)
    AND created >= -1d
    ORDER BY created DESC
"""
```

**Common JQL Modifications:**

Change time range:
```sql
created >= -7d   # Last 7 days
created >= -30d  # Last 30 days
created >= "2025-01-01"  # Specific date
```

Add project filter:
```sql
AND project = "DBAASOPS"
```

Filter by assignee:
```sql
AND assignee = currentUser()
AND assignee = "john.doe@oracle.com"
```

Filter by status:
```sql
AND status in ("In Progress", "Resolved")
```

### Adjusting Max Results

In `.env` file:
```bash
MAX_RESULTS=200  # Fetch up to 200 issues
```

Or modify directly in the script:
```python
MAX_RESULTS = int(os.getenv('MAX_RESULTS', 500))
```

---

## Output Files

The script generates three files in the `reports/` directory:

### Important Notes:
- All output files are saved in the **`reports/`** subdirectory
- The `reports/` directory is **automatically created** if it doesn't exist
- **Previous files are automatically deleted** before each run to ensure fresh data
- Only the latest generated files are kept in the `reports/` directory

### 1. `reports/jira_table.csv`
Complete dataset with all fetched JIRA issues.

**Columns:**
- Key
- Summary
- Assignee
- Reporter
- P (Priority)
- Status
- Resolution
- Created
- Updated
- Due
- Labels

**Use case:** Raw data for further analysis, Excel import, etc.

### 2. `reports/jira_status_report.csv`
Filtered report containing only issues with success/failed labels.

**Columns:**
- JIRA ID
- Status (Success/Failed)
- Link (JIRA URL)

**Use case:** Quick status overview, importing into other tools

### 3. `reports/jira_status_report.html`
Interactive HTML report with styling and clickable links.

**Features:**
- Clickable JIRA ticket links
- Color-coded status (Green = Success, Red = Failed)
- Summary statistics (Total, Success count, Failed count)
- Professional styling

**Use case:** Sharing with team, embedding in dashboards, presentations

**To view:**
```bash
# Windows
start reports\jira_status_report.html

# Linux
xdg-open reports/jira_status_report.html

# Mac
open reports/jira_status_report.html
```

---

## Troubleshooting

### Issue 1: "Missing JIRA credentials" Error

**Error message:**
```
✗ ERROR: Missing JIRA credentials
Please create a .env file in the project root...
```

**Solution:**
1. Ensure `.env` file exists in the same directory as `jira_table_analyze.py`
2. Verify `.env` contains `JIRA_USERNAME` and `JIRA_API_TOKEN`
3. Check for typos in variable names (they are case-sensitive)

---

### Issue 2: "Failed to connect to JIRA" Error

**Possible causes:**
- Invalid credentials
- Incorrect JIRA URL
- Network connectivity issues
- API token expired

**Solutions:**

1. **Verify credentials:**
   ```bash
   # Check .env file
   cat .env  # Linux/Mac
   type .env  # Windows
   ```

2. **Test JIRA URL in browser:**
   - Open your JIRA URL in a web browser
   - Ensure you can access it and log in

3. **Regenerate API token:**
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Delete old token and create a new one
   - Update `.env` file with new token

4. **Check network/firewall:**
   - Ensure your network allows HTTPS connections to JIRA
   - Try accessing JIRA from the same machine via browser

---

### Issue 3: "No module named 'jira'" Error

**Error message:**
```
ModuleNotFoundError: No module named 'jira'
```

**Solution:**
```bash
# Ensure virtual environment is activated
# Then reinstall dependencies
pip install -r requirements.txt

# Or install jira package directly
pip install jira
```

---

### Issue 4: "No module named 'dotenv'" Error

**Solution:**
```bash
pip install python-dotenv
```

---

### Issue 5: Authentication Error (401 Unauthorized)

**Error message:**
```
JIRAError HTTP 401 url: https://jira-sd.mc1.oracleiaas.com/rest/api/2/...
```

**Solutions:**

1. **For Oracle Internal JIRA:**
   - Standard API tokens may not work
   - Contact your IT administrator for proper authentication method
   - May require OAuth, SSO, or different token generation process

2. **For Atlassian Cloud:**
   - Verify you're using your **email address** as username (not username)
   - Ensure API token is valid and not expired
   - Try generating a fresh API token

---

### Issue 6: No Issues Found / Empty Results

**Possible causes:**
- JQL query returns no results
- Incorrect filter criteria
- No issues match the date range

**Solutions:**

1. **Test JQL query in JIRA web interface:**
   - Go to your JIRA instance
   - Click **Filters** → **Advanced Issue Search**
   - Paste your JQL query
   - Verify it returns results

2. **Adjust date range:**
   ```python
   # Change from -1d to -7d or more
   created >= -7d
   ```

3. **Simplify query for testing:**
   ```python
   JQL_QUERY = "project = DBAASOPS AND created >= -30d ORDER BY created DESC"
   ```

---

### Issue 7: Permission Denied Errors

**Error message:**
```
JIRAError HTTP 403 url: ...
```

**Solution:**
- Your JIRA account lacks permissions to view these issues
- Contact JIRA administrator to grant read access
- Verify you can see these issues in the JIRA web interface

---

### Issue 8: SSL Certificate Errors

**Error message:**
```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Solution (Use with caution - only for internal/trusted networks):**

Add SSL verification disable (NOT recommended for production):
```python
# In jira_table_analyze.py, modify _connect method:
self.jira = JIRA(
    server=self.jira_url,
    basic_auth=(username, api_token),
    options={'verify': False}  # Only for trusted internal networks
)
```

---

## Differences from Image-Based Script

| Feature | Image-Based (`jira_table_processor_antigravity.py`) | API-Based (`jira_table_analyze.py`) |
|---------|------------------------------------------------------|-------------------------------------|
| **Data Source** | Screenshot image (OCR) | JIRA REST API |
| **Accuracy** | Depends on OCR quality | 100% accurate |
| **Speed** | Slower (image processing) | Faster (direct API) |
| **Scalability** | Limited to visible rows | Can fetch 100s of issues |
| **Real-time** | Manual screenshot needed | Always current data |
| **Dependencies** | OpenCV, Tesseract, pytesseract | jira, python-dotenv |
| **Setup Complexity** | Medium (Tesseract install) | Simple (pip install) |
| **Authentication** | None | JIRA credentials required |

---

## Advanced Configuration

### Running with Different Credentials

You can override `.env` settings by setting environment variables:

```bash
# Linux/Mac
export JIRA_USERNAME="different.user@oracle.com"
export JIRA_API_TOKEN="different_token"
python jira_table_analyze.py

# Windows Command Prompt
set JIRA_USERNAME=different.user@oracle.com
set JIRA_API_TOKEN=different_token
python jira_table_analyze.py

# Windows PowerShell
$env:JIRA_USERNAME="different.user@oracle.com"
$env:JIRA_API_TOKEN="different_token"
python jira_table_analyze.py
```

### Scheduling Automated Runs

#### Linux/Mac (cron):
```bash
# Edit crontab
crontab -e

# Run daily at 8 AM
0 8 * * * cd /path/to/project && /path/to/venv/bin/python jira_table_analyze.py
```

#### Windows (Task Scheduler):
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., Daily at 8:00 AM)
4. Action: Start a program
5. Program: `C:\path\to\venv\Scripts\python.exe`
6. Arguments: `jira_table_analyze.py`
7. Start in: `C:\path\to\project`

---

## Support & Additional Resources

### JIRA API Documentation
- Official JIRA REST API: https://developer.atlassian.com/cloud/jira/platform/rest/v2/
- JQL Reference: https://support.atlassian.com/jira-service-management-cloud/docs/use-advanced-search-with-jira-query-language-jql/

### Python JIRA Library
- Documentation: https://jira.readthedocs.io/
- GitHub: https://github.com/pycontribs/jira

### Related Files in This Project
- `COMPREHENSIVE_PROMPT.md` - Original requirements and specifications
- `from_desktop/INSTALLATION.md` - Installation guide for image-based processor
- `CLAUDE.md` - Architecture and development guide

---

## Security Best Practices

1. **Never commit `.env` file** - It's in `.gitignore` for a reason
2. **Rotate API tokens regularly** - Generate new tokens every 90 days
3. **Use read-only tokens** - Don't grant write permissions unless needed
4. **Monitor token usage** - Check JIRA audit logs periodically
5. **Revoke unused tokens** - Delete tokens you're no longer using

---

## License & Disclaimer

This tool is provided as-is for internal use. Ensure compliance with your organization's security policies before using with production JIRA instances.
