# Comprehensive Prompt: JIRA API Analysis and Status Report Generation

## Objective
Create a Python program that connects directly to JIRA via API, fetches issues using JQL queries, analyzes labels to determine status, and generates comprehensive reports with hyperlinks.

---

## Overview

This system provides direct JIRA API integration for:
- Real-time data retrieval using JQL queries
- Automatic label analysis for success/failed status determination
- Multiple report formats (CSV, HTML, console output)
- Professional styling with clickable hyperlinks
- Summary statistics and categorization

---

## Requirements

### Step 1: JIRA API Connection and Authentication
**Task:** Establish secure connection to JIRA instance using API token authentication.

**Details:**
- Use environment variables for credentials (`.env` file)
- Support token-based authentication
- Handle connection errors gracefully
- Validate credentials before proceeding

**Environment Variables Required:**
```env
JIRA_URL=https://jira-sd.mc1.oracleiaas.com
JIRA_API_TOKEN=your_api_token_here
MAX_RESULTS=100
```

**Authentication Method:**
- Token-based authentication (recommended for security)
- No hardcoded credentials in code
- Use `python-dotenv` for environment variable management

---

### Step 2: Data Extraction via JQL Query
**Task:** Fetch JIRA issues using JQL (JIRA Query Language) queries.

**Details:**
- Accept JQL query string as input
- Fetch configurable number of results (default: 100)
- Extract all relevant fields from each issue
- Convert to structured pandas DataFrame

**Fields to Extract:**
1. **Key** - JIRA ticket ID (e.g., DBAASOPS-466646)
2. **Summary** - Issue description/title
3. **Assignee** - Person assigned to the ticket
4. **Reporter** - Person who created the ticket
5. **Priority** - Issue priority level
6. **Status** - Current ticket status (e.g., Resolved, Open)
7. **Resolution** - Resolution status (e.g., Done, Unresolved)
8. **Created** - Creation date (formatted as YYYY-MM-DD)
9. **Updated** - Last update date (formatted as YYYY-MM-DD)
10. **Due** - Due date (if set)
11. **Labels** - All labels associated with the ticket (space-separated)

**JQL Query Example:**
```jql
text ~ metricsV2.EXADATA.dbaas.patchCloudExaInfra.APPLY.WORKER.Failure
AND labels in (oneview_triagex_started,oneview_triagex_success,oneview_triagex_failed)
AND created >= -3d
ORDER BY created DESC
```

**Implementation Requirements:**
- Use `jira` Python library for API interaction
- Handle pagination for large result sets
- Parse and format dates appropriately
- Handle missing/null fields gracefully (e.g., unassigned issues)

---

### Step 3: Save Original Data to CSV
**Task:** Export complete extracted data to CSV format for archival and analysis.

**Details:**
- Save to: `reports/jira_table.csv`
- Include all columns and rows without modification
- Use UTF-8 encoding
- Include headers

**CSV Structure:**
```
Key,Summary,Assignee,Reporter,P,Status,Resolution,Created,Updated,Due,Labels
DBAASOPS-467005,[IAD] metricsV2...,B V A M VARMA PENMETSA,...,High,Resolved,Resolved,2025-12-01,...
```

---

### Step 4: Print Original Table to Console
**Task:** Display the extracted table in a human-readable format in the console.

**Details:**
- Print complete table with all columns and rows
- Use proper formatting with aligned columns
- Include headers and separators
- Handle wide content appropriately
- Make output readable in terminal

**Output Format Example:**
```
======================================================================================
JIRA ISSUES TABLE
======================================================================================
Key              Summary                           Assignee            Status    Labels
--------------------------------------------------------------------------------------
DBAASOPS-467005  Tracking: [IAD] metricsV2...     B V A M VARMA...    Resolved  auto-analysis...
DBAASOPS-466646  Tracking: [PHX] metricsV2...     Gurudatta...        Resolved  auto-analysis...
======================================================================================
```

---

### Step 5: Label Analysis and Status Report Generation
**Task:** Process each row, analyze labels, and generate a filtered status report.

**Processing Logic:**

For each issue in the DataFrame:
1. **Read the Key** (JIRA ticket ID)
2. **Read the Labels** (space-separated label string)
3. **Read the Created date**
4. **Generate JIRA hyperlink** using format:
   ```
   {JIRA_URL}/browse/{KEY}
   ```
5. **Analyze Labels:**
   - If label contains `"oneview_triagex_failed"` → Status: **"Failed"**
   - If label contains `"oneview_triagex_success"` → Status: **"Success"**
   - If neither label exists → **Skip this row** (don't add to report)

**Output DataFrame Structure:**
- **JIRA ID**: The ticket key
- **Status**: "Success" or "Failed"
- **Date**: Creation date (YYYY-MM-DD format)
- **Link**: Full hyperlink to the JIRA issue

**Example:**
```
Input Issue:
- Key: DBAASOPS-466646
- Labels: "auto-analysis-v1e oneview_triagex_success multicloud-"
- Created: 2025-11-29

Output Report Row:
- JIRA ID: DBAASOPS-466646
- Status: Success
- Date: 2025-11-29
- Link: https://jira-sd.mc1.oracleiaas.com/browse/DBAASOPS-466646
```

**Function Requirements:**
- Accept DataFrame as input
- Return new DataFrame with filtered results
- Handle edge cases (missing labels, null values)
- Case-insensitive label matching
- Reusable and modular design

---

### Step 6: Save Status Report to CSV
**Task:** Export the status report to CSV format.

**Details:**
- Save to: `reports/jira_status_report.csv`
- Include headers: JIRA ID, Status, Date, Link
- Comma-separated format
- UTF-8 encoding

**CSV Structure:**
```csv
JIRA ID,Status,Date,Link
DBAASOPS-467005,Success,2025-12-01,https://jira-sd.mc1.oracleiaas.com/browse/DBAASOPS-467005
DBAASOPS-466646,Success,2025-11-29,https://jira-sd.mc1.oracleiaas.com/browse/DBAASOPS-466646
```

---

### Step 7: Generate HTML Report with Styling
**Task:** Create a professional HTML report with clickable links and visual styling.

**Details:**
- Save to: `reports/jira_status_report.html`
- Include clickable hyperlinks for JIRA IDs
- Color-coded status badges
- Summary statistics section
- Responsive design
- Professional JIRA-like styling

**HTML Features:**

1. **Summary Section:**
   - Total issues count
   - Success count
   - Failed count
   - Comma-separated list of successful JIRA IDs with links
   - Comma-separated list of failed JIRA IDs with links

2. **Status Table:**
   - Columns: JIRA ID, Status, Date Created
   - Clickable JIRA IDs (open in new tab)
   - Color-coded status badges:
     - Success: Green background (#e3fcef), dark green text (#006644)
     - Failed: Red background (#ffebe6), dark red text (#bf2600)
   - Hover effects on rows

3. **Styling Requirements:**
   - Modern, clean design
   - JIRA-inspired color scheme
   - Blue hyperlinks (#0052CC)
   - Professional typography
   - Proper spacing and alignment
   - Box shadows for depth
   - Rounded corners

**HTML Example Structure:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>JIRA Status Report</title>
    <style>
        /* Professional JIRA-like styling */
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
        .status-success { background-color: #e3fcef; color: #006644; }
        .status-failed { background-color: #ffebe6; color: #bf2600; }
        /* ... more styles ... */
    </style>
</head>
<body>
    <h1>JIRA Status Report</h1>
    <div class="summary">
        <h3>Summary</h3>
        <p><strong>Total Issues:</strong> 7</p>
        <p><strong>Success:</strong> 7</p>
        <p><strong>Failed:</strong> 0</p>
        <h4>Successful JIRA Tickets:</h4>
        <p><a href="...">DBAASOPS-467005</a>, <a href="...">DBAASOPS-466646</a>, ...</p>
    </div>
    <table>
        <!-- Status table with clickable links -->
    </table>
</body>
</html>
```

---

### Step 8: Print Status Report to Console
**Task:** Display the final status report in a formatted, readable manner in the console.

**Details:**
- Formatted table with columns: JIRA ID, Status, Link
- Include summary statistics
- Clear headers and separators
- Aligned columns

**Output Example:**
```
====================================================================================================
JIRA STATUS REPORT
====================================================================================================
        JIRA ID  Status       Date                                                      Link
----------------------------------------------------------------------------------------------------
DBAASOPS-467005 Success 2025-12-01 https://jira-sd.mc1.oracleiaas.com/browse/DBAASOPS-467005
DBAASOPS-466646 Success 2025-11-29 https://jira-sd.mc1.oracleiaas.com/browse/DBAASOPS-466646
====================================================================================================

Summary:
  Total Issues: 7
  Success: 7
  Failed: 0
====================================================================================================
```

---

## Program Structure

### Class Design
```python
class JiraTableAnalyzer:
    """Main class for JIRA API analysis and report generation."""

    def __init__(self, jira_url: str, api_token: str)
    def _connect(self, api_token: str) -> None
    def fetch_issues_from_jira(self, jql_query: str, max_results: int = 100) -> pd.DataFrame
    def save_to_csv(self, df: pd.DataFrame, output_path: str) -> str
    def print_table(self, df: pd.DataFrame) -> None
    def process_labels_and_create_status_report(self, df: pd.DataFrame) -> pd.DataFrame
    def print_status_report(self, status_df: pd.DataFrame) -> None
    def save_status_report_to_csv(self, status_df: pd.DataFrame, output_path: str) -> str
    def create_html_report(self, status_df: pd.DataFrame, output_path: str) -> str
    def run(self, jql_query: str, max_results: int = 100) -> None
```

### Method Descriptions

**`__init__(self, jira_url: str, api_token: str)`**
- Initialize the analyzer with JIRA connection details
- Automatically establish connection during initialization
- Store JIRA URL and connection object

**`_connect(self, api_token: str)`**
- Private method to establish JIRA connection
- Use token-based authentication
- Handle connection errors with clear messages
- Print success/failure status

**`fetch_issues_from_jira(self, jql_query: str, max_results: int = 100)`**
- Execute JQL query against JIRA API
- Fetch specified fields for each issue
- Parse and format data appropriately
- Return pandas DataFrame with all issue data
- Handle API errors gracefully

**`save_to_csv(self, df: pd.DataFrame, output_path: str)`**
- Export DataFrame to CSV format
- Ensure UTF-8 encoding
- Print confirmation message with file path

**`print_table(self, df: pd.DataFrame)`**
- Display DataFrame in formatted table in console
- Set pandas display options for better readability
- Include headers and borders

**`process_labels_and_create_status_report(self, df: pd.DataFrame)`**
- Iterate through each issue
- Analyze labels for success/failed indicators
- Create filtered DataFrame with only relevant issues
- Generate hyperlinks for each issue
- Return status report DataFrame

**`print_status_report(self, status_df: pd.DataFrame)`**
- Display status report in formatted console output
- Include summary statistics
- Show total, success, and failed counts

**`save_status_report_to_csv(self, status_df: pd.DataFrame, output_path: str)`**
- Export status report to CSV
- Include proper headers
- Print confirmation message

**`create_html_report(self, status_df: pd.DataFrame, output_path: str)`**
- Generate professional HTML report
- Include inline CSS styling
- Create clickable hyperlinks
- Add summary statistics section
- Implement color-coded status badges

**`run(self, jql_query: str, max_results: int = 100)`**
- Orchestrate the complete workflow
- Execute all steps in sequence
- Handle directory creation and cleanup
- Print progress messages for each step

---

## Main Workflow

```python
def main():
    """Main execution function."""

    # 1. Load environment variables
    load_dotenv()
    JIRA_URL = os.getenv('JIRA_URL', 'https://jira-sd.mc1.oracleiaas.com')
    JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
    MAX_RESULTS = int(os.getenv('MAX_RESULTS', 100))

    # 2. Validate credentials
    if not JIRA_API_TOKEN:
        print("ERROR: Missing JIRA_API_TOKEN in .env file")
        return

    # 3. Define JQL query
    JQL_QUERY = """
    text ~ metricsV2.EXADATA.dbaas.patchCloudExaInfra.APPLY.WORKER.Failure
    AND labels in (oneview_triagex_started,oneview_triagex_success,oneview_triagex_failed)
    AND created >= -3d
    ORDER BY created DESC
    """

    # 4. Create analyzer instance
    analyzer = JiraTableAnalyzer(JIRA_URL, JIRA_API_TOKEN)

    # 5. Run the complete analysis
    analyzer.run(JQL_QUERY, MAX_RESULTS)

if __name__ == "__main__":
    main()
```

### Workflow Steps (Inside `run()` method):

```python
def run(self, jql_query: str, max_results: int = 100):
    # Step 1: Create/clean reports directory
    # Step 2: Fetch issues from JIRA
    df = self.fetch_issues_from_jira(jql_query, max_results)

    # Step 3: Save original data to CSV
    self.save_to_csv(df, 'reports/jira_table.csv')

    # Step 4: Print original table
    self.print_table(df)

    # Step 5: Process labels and create status report
    status_df = self.process_labels_and_create_status_report(df)

    # Step 6: Save status report to CSV
    self.save_status_report_to_csv(status_df, 'reports/jira_status_report.csv')

    # Step 7: Create HTML report with hyperlinks
    self.create_html_report(status_df, 'reports/jira_status_report.html')

    # Step 8: Print final status report
    self.print_status_report(status_df)
```

---

## Technical Specifications

### Dependencies
```python
# requirements.txt
pandas>=2.0.0
jira>=3.5.0
python-dotenv>=1.0.0
```

### Installation
```bash
pip install -r requirements.txt
```

### Environment Setup

1. **Create `.env` file in project root:**
```env
JIRA_URL=https://jira-sd.mc1.oracleiaas.com
JIRA_API_TOKEN=your_actual_api_token_here
MAX_RESULTS=100
```

2. **Generate JIRA API Token:**
   - Log into your JIRA instance
   - Go to Account Settings → Security → API Tokens
   - Create new token
   - Copy token to `.env` file

3. **Never commit `.env` to version control:**
```bash
# Add to .gitignore
.env
```

### Execution
```bash
python jira_table_analyze.py
```

---

## Expected Output Files

### 1. `reports/jira_table.csv`
- Complete extracted data from JIRA
- All columns and rows preserved
- CSV format with headers
- UTF-8 encoding

**Example Content:**
```csv
Key,Summary,Assignee,Reporter,P,Status,Resolution,Created,Updated,Due,Labels
DBAASOPS-467005,"Tracking: [IAD] metricsV2...",B V A M VARMA PENMETSA,...,High,Resolved,Resolved,2025-12-01,2025-12-01,,auto-analysis-v1e oneview_triagex_success...
```

### 2. `reports/jira_status_report.csv`
- Filtered status report
- Only rows with success/failed labels
- Columns: JIRA ID, Status, Date, Link

**Example Content:**
```csv
JIRA ID,Status,Date,Link
DBAASOPS-467005,Success,2025-12-01,https://jira-sd.mc1.oracleiaas.com/browse/DBAASOPS-467005
DBAASOPS-466646,Success,2025-11-29,https://jira-sd.mc1.oracleiaas.com/browse/DBAASOPS-466646
```

### 3. `reports/jira_status_report.html`
- Professional HTML report
- Clickable hyperlinks
- Color-coded status badges
- Summary statistics
- JIRA-inspired styling
- Opens in any web browser

---

## Error Handling Requirements

### 1. Connection Errors
- Validate JIRA URL format
- Check network connectivity
- Handle authentication failures
- Provide clear error messages

### 2. API Errors
- Handle rate limiting
- Manage timeout issues
- Deal with invalid JQL queries
- Handle empty result sets

### 3. Data Processing Errors
- Handle missing/null fields
- Deal with malformed data
- Validate column existence
- Handle empty labels gracefully

### 4. File I/O Errors
- Check write permissions
- Verify directory existence
- Handle disk space issues
- Create directories if needed

**Error Handling Example:**
```python
try:
    analyzer = JiraTableAnalyzer(JIRA_URL, JIRA_API_TOKEN)
    analyzer.run(JQL_QUERY, MAX_RESULTS)
except KeyboardInterrupt:
    print("\n✗ Operation cancelled by user.")
except Exception as e:
    print(f"✗ Error: {e}")
    traceback.print_exc()
```

---

## Security Best Practices

1. **Never hardcode credentials**
   - Always use environment variables
   - Use `.env` file for local development
   - Use secure secret management in production

2. **Protect API tokens**
   - Add `.env` to `.gitignore`
   - Rotate tokens regularly
   - Use minimum required permissions

3. **Secure file handling**
   - Validate output paths
   - Use appropriate file permissions
   - Don't expose sensitive data in logs

4. **API rate limiting**
   - Respect JIRA API rate limits
   - Implement retry logic with backoff
   - Use pagination for large result sets

---

## Performance Considerations

- **Fast execution:** Process 100 issues in under 5 seconds (network dependent)
- **Memory efficient:** Handle large result sets (1000+ issues)
- **Scalable:** Support multiple concurrent queries
- **Minimal dependencies:** Only essential libraries required
- **Efficient API calls:** Fetch only required fields to reduce payload

---

## Customization Options

### 1. Change JQL Query
```python
JQL_QUERY = """
project = DBAASOPS
AND status = Resolved
AND created >= -7d
ORDER BY updated DESC
"""
```

### 2. Modify Label Matching
```python
# In process_labels_and_create_status_report()
if 'custom_label_failed' in labels:
    status = "Failed"
elif 'custom_label_success' in labels:
    status = "Success"
elif 'custom_label_pending' in labels:
    status = "Pending"
```

### 3. Change Output Paths
```python
self.save_to_csv(df, '/custom/path/output.csv')
```

### 4. Customize Report Styling
Modify the CSS in the `create_html_report()` method to match your organization's branding.

### 5. Add More Fields
```python
# In fetch_issues_from_jira()
fields='key,summary,assignee,priority,status,labels,customfield_12345'
```

---

## Testing Checklist

- [ ] Successfully connect to JIRA API
- [ ] Authenticate with API token
- [ ] Execute JQL query correctly
- [ ] Extract all required fields
- [ ] Handle missing/null values
- [ ] Format dates properly
- [ ] Generate valid CSV files
- [ ] Print formatted tables to console
- [ ] Identify "oneview_triagex_failed" labels
- [ ] Identify "oneview_triagex_success" labels
- [ ] Create correct hyperlinks
- [ ] Generate HTML with working links
- [ ] Handle rows with no matching labels
- [ ] Display summary statistics
- [ ] Clean and recreate reports directory
- [ ] Handle connection errors gracefully
- [ ] Process large result sets efficiently

---

## Usage Example

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file
cat > .env << EOF
JIRA_URL=https://jira-sd.mc1.oracleiaas.com
JIRA_API_TOKEN=your_token_here
MAX_RESULTS=100
EOF

# 3. Run the program
python jira_table_analyze.py

# 4. Expected output files in reports/ directory:
# - reports/jira_table.csv
# - reports/jira_status_report.csv
# - reports/jira_status_report.html

# 5. View HTML report in browser
start reports/jira_status_report.html  # Windows
open reports/jira_status_report.html   # macOS
xdg-open reports/jira_status_report.html  # Linux
```

---

## Example Console Output

```
================================================================================
JIRA TABLE ANALYZER
================================================================================
JIRA Instance: https://jira-sd.mc1.oracleiaas.com
Query Filter: text ~ metricsV2.EXADATA.dbaas.patchCloudExaInfra...
Max Results: 100
================================================================================
Connecting to JIRA at https://jira-sd.mc1.oracleiaas.com...
✓ Successfully connected to JIRA

================================================================================
JIRA TABLE ANALYZER - Starting Analysis
================================================================================

[Setup] Creating reports/ directory...
✓ reports/ directory ready

[Step 1] Fetching issues from JIRA...
✓ Found 7 issues

[Step 2] Saving original data to CSV...
✓ Saved table to reports/jira_table.csv

[Step 3] Displaying original table...
[Formatted table output]

[Step 4] Processing labels and creating status report...

[Step 5] Saving status report to CSV...
✓ Saved status report to reports/jira_status_report.csv

[Step 6] Creating HTML report with hyperlinks...
✓ Saved HTML report to reports/jira_status_report.html

[Step 7] Displaying final status report...
[Status report with summary]

================================================================================
✓ Analysis Complete!
================================================================================

Generated Files in reports/ directory:
  • reports/jira_table.csv - Complete JIRA data
  • reports/jira_status_report.csv - Status report (Success/Failed)
  • reports/jira_status_report.html - Interactive HTML report
```

---

## Success Criteria

✅ Successfully connect to JIRA API with token authentication
✅ Execute JQL queries and fetch results
✅ Extract all required fields from issues
✅ Handle missing/null values gracefully
✅ Save complete data to CSV
✅ Display formatted table in console
✅ Analyze labels correctly (success/failed)
✅ Generate status report with correct categorization
✅ Create working hyperlinks to JIRA issues
✅ Export status report to CSV
✅ Generate professional HTML report with styling
✅ Display summary statistics (total, success, failed)
✅ Color-code status badges in HTML
✅ Handle errors gracefully with clear messages
✅ Use secure credential management (.env)
✅ Code is modular and reusable
✅ Documentation is clear and comprehensive

---

## Key Features

### 1. Direct API Integration
- Real-time data access
- No OCR errors or image quality issues
- Always up-to-date information
- Supports complex JQL queries

### 2. Secure Authentication
- Token-based authentication
- Environment variable management
- No hardcoded credentials
- `.env` file for local development

### 3. Comprehensive Reports
- Multiple output formats (CSV, HTML, console)
- Professional styling and formatting
- Clickable hyperlinks
- Summary statistics

### 4. Label Analysis
- Automatic status determination
- Configurable label matching
- Handles multiple label formats
- Case-insensitive matching

### 5. Modular Design
- Reusable class structure
- Independent methods
- Easy to extend and customize
- Clean separation of concerns

### 6. Robust Error Handling
- Connection validation
- API error management
- Graceful fallbacks
- Clear error messages

---

## End Result

A complete, professional Python solution that:
1. Connects directly to JIRA via REST API
2. Fetches issues using flexible JQL queries
3. Extracts comprehensive issue data
4. Analyzes ticket labels automatically
5. Generates professional status reports
6. Provides multiple output formats
7. Creates clickable links for easy navigation
8. Presents data in clear, readable formats
9. Uses secure credential management
10. Can be easily integrated into workflows
11. Is maintainable and extensible

---

*This prompt can be used to recreate the entire JIRA API analysis system from scratch.*
