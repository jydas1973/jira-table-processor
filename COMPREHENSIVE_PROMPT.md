# Comprehensive Prompt: JIRA Table Image Processing and Status Report Generation

## Objective
Create a Python program that extracts tabular data from a JIRA screenshot image, converts it to structured text/CSV format, analyzes the labels to determine status, and generates comprehensive reports with hyperlinks.

---

## Requirements

### Step 1: Image to Table Conversion
**Task:** Develop a Python program to convert a screenshot image containing a JIRA table into a structured tabular format.

**Details:**
- Input: Screenshot image file containing a JIRA issue tracking table
- Output: Structured table in both CSV and text format
- Preserve ALL data without modification
- Maintain exact column structure and values

**Columns to Extract:**
1. Key (JIRA ticket ID)
2. Summary (Issue description)
3. Assignee (Person assigned to the ticket)
4. Reporter (Person who created the ticket)
5. P (Priority)
6. Status (Current ticket status)
7. Resolution (Resolution status)
8. Created (Creation date)
9. Updated (Last update date)
10. Due (Due date)
11. Labels (All labels associated with the ticket)

**Implementation Requirements:**
- Use Python with libraries: pandas, Pillow, opencv-python
- Create a reusable class/function for table extraction
- Ensure no data is lost or modified during extraction
- Handle all data types (text, dates, empty fields)

---

### Step 2: Print Original Table in Text Format
**Task:** Display the extracted table in a human-readable text format.

**Details:**
- Print the complete table with all columns and rows
- Use proper formatting with aligned columns
- Include headers
- Make output readable in terminal/console
- Display complete content without truncation

**Output Format Example:**
```
==============================================================================
ORIGINAL JIRA TABLE
==============================================================================
Key              Summary                           Assignee        Status
------------------------------------------------------------------------------
DBAASOPS-465465  Tracking: [EU-AMSTERDAM-1]...     Devesh Sahu     RESOLVED
DBAASOPS-465302  Tracking: [SA-VALPARAISO-1]...    Eric Du         RESOLVED
...
==============================================================================
```

---

### Step 3: Label Analysis and Status Report Generation
**Task:** Create a separate API/function that processes each row, analyzes labels, and generates a status report.

**Processing Logic:**

For each row in the table:
1. **Read the Key value** (JIRA ticket ID)
2. **Read the Labels value** (comma/space-separated label string)
3. **Create/Update Status Report Table** with two columns:
   - "JIRA ID"
   - "Status"
4. **Analyze Labels:**
   - If label contains `"oneview_triagex_failed"`:
     - Add JIRA ID to report with hyperlink
     - Set Status as "Failed"
   - If label contains `"oneview_triagex_success"`:
     - Add JIRA ID to report with hyperlink
     - Set Status as "Success"
   - If neither label exists, skip the row (don't add to report)

**Hyperlink Format:**
```
https://jira-sd.mc1.oracleiaas.com/browse/{JIRA_KEY}
```

**Example:**
- Key: `DBAASOPS-465465`
- Link: `https://jira-sd.mc1.oracleiaas.com/browse/DBAASOPS-465465`

**API Requirements:**
- Function should accept DataFrame as input
- Return a new DataFrame with JIRA ID, Link, and Status
- Should be reusable with different inputs
- Handle edge cases (missing labels, empty strings)

---

### Step 4: Print Status Report to End User
**Task:** Display the final status report in a clear, formatted manner.

**Output Requirements:**

1. **Console/Terminal Output:**
   - Formatted table with columns: JIRA ID, Status, Link
   - Aligned columns for readability
   - Clear headers and separators

2. **CSV Export:**
   - Save to file: `jira_status_report.csv`
   - Include headers: JIRA ID, Link, Status
   - Comma-separated format

3. **HTML Report with Clickable Links:**
   - Save to file: `jira_status_report.html`
   - Professional styling
   - Clickable hyperlinks for JIRA IDs
   - Summary statistics (Total, Success count, Failed count)
   - Color coding (Green for Success, Red for Failed)

**Example Output:**
```
====================================================================================================
JIRA STATUS REPORT
====================================================================================================
JIRA ID              Status          Link
----------------------------------------------------------------------------------------------------
DBAASOPS-465465      Success         https://jira-sd.mc1.oracleiaas.com/browse/DBAASOPS-465465
DBAASOPS-465302      Failed          https://jira-sd.mc1.oracleiaas.com/browse/DBAASOPS-465302
DBAASOPS-465216      Success         https://jira-sd.mc1.oracleiaas.com/browse/DBAASOPS-465216
DBAASOPS-465212      Success         https://jira-sd.mc1.oracleiaas.com/browse/DBAASOPS-465212
====================================================================================================

Summary:
  Total Issues: 4
  Success: 3
  Failed: 1
```

---

## Program Structure

### Class Design
```python
class JiraTableProcessor:
    def __init__(self, image_path: str)
    def extract_table_from_image(self) -> pd.DataFrame
    def save_to_csv(self, df: pd.DataFrame, output_path: str) -> str
    def print_table(self, df: pd.DataFrame) -> None
    def process_labels_and_create_status_report(self, df: pd.DataFrame) -> pd.DataFrame
    def print_status_report(self, status_df: pd.DataFrame) -> None
    def save_status_report_to_csv(self, status_df: pd.DataFrame, output_path: str) -> str
    def create_html_report(self, status_df: pd.DataFrame, output_path: str) -> str
    def run(self) -> Tuple[pd.DataFrame, pd.DataFrame]
```

### Main Workflow
```python
def main():
    # 1. Initialize processor with image path
    processor = JiraTableProcessor(image_path)
    
    # 2. Extract table from image
    original_df = processor.extract_table_from_image()
    
    # 3. Save original data to CSV
    processor.save_to_csv(original_df, 'jira_table.csv')
    
    # 4. Print original table
    processor.print_table(original_df)
    
    # 5. Process labels and create status report
    status_df = processor.process_labels_and_create_status_report(original_df)
    
    # 6. Save status report to CSV
    processor.save_status_report_to_csv(status_df, 'jira_status_report.csv')
    
    # 7. Create HTML report with hyperlinks
    processor.create_html_report(status_df, 'jira_status_report.html')
    
    # 8. Print final status report
    processor.print_status_report(status_df)
```

---

## Technical Specifications

### Dependencies
```python
# requirements.txt
pandas>=2.0.0
Pillow>=10.0.0
opencv-python>=4.8.0
openpyxl>=3.1.0
```

### Installation
```bash
pip install -r requirements.txt
```

### Execution
```bash
python jira_table_processor.py
```

---

## Expected Output Files

1. **jira_table.csv**
   - Original extracted data
   - All columns preserved
   - CSV format with headers

2. **jira_status_report.csv**
   - Processed status report
   - Columns: JIRA ID, Link, Status
   - Only rows with success/failed labels

3. **jira_status_report.html**
   - HTML report with styling
   - Clickable hyperlinks
   - Summary statistics
   - Color-coded status indicators

4. **jira_table_processor.py**
   - Main Python program
   - Complete with all functions
   - Reusable and modular

---

## Example Data Flow

### Input (Screenshot):
```
┌──────────────┬─────────────────────┬──────────┬────────┬─────────────────────────────────┐
│ Key          │ Summary             │ Assignee │ Status │ Labels                          │
├──────────────┼─────────────────────┼──────────┼────────┼─────────────────────────────────┤
│DBAASOPS-46.. │ Tracking: [EU-AM..] │ Devesh.. │RESOLVED│...oneview_triagex_success       │
│DBAASOPS-46.. │ Tracking: [SA-VA..] │ Eric Du  │RESOLVED│...oneview_triagex_failed        │
└──────────────┴─────────────────────┴──────────┴────────┴─────────────────────────────────┘
```

### Processing:
```
Step 1: Extract → DataFrame with all columns
Step 2: Print → Formatted text table
Step 3: Analyze Labels → Filter rows by success/failed
Step 4: Generate → Status report with links
```

### Output (Status Report):
```
┌─────────────────┬─────────┬──────────────────────────────────────────────┐
│ JIRA ID         │ Status  │ Link                                         │
├─────────────────┼─────────┼──────────────────────────────────────────────┤
│ DBAASOPS-465465 │ Success │ https://jira-sd.mc1.oracleiaas.com/browse... │
│ DBAASOPS-465302 │ Failed  │ https://jira-sd.mc1.oracleiaas.com/browse... │
└─────────────────┴─────────┴──────────────────────────────────────────────┘
```

---

## Key Features

### 1. Data Integrity
- No modification of original data
- Exact preservation of all values
- Complete column retention

### 2. Reusability
- Modular function design
- Parameterized APIs
- Easy to extend for new requirements

### 3. Multiple Output Formats
- CSV for data processing
- Text for terminal viewing
- HTML for presentation/sharing

### 4. Robust Processing
- Handle missing labels gracefully
- Skip rows without target labels
- Maintain table consistency

### 5. Professional Reporting
- Clear formatting
- Summary statistics
- Clickable hyperlinks
- Visual styling (HTML)

---

## Error Handling Requirements

1. **Image Loading Errors:**
   - Check file exists
   - Verify image format
   - Handle corrupted files

2. **Data Processing Errors:**
   - Handle empty labels
   - Deal with malformed data
   - Validate column existence

3. **File I/O Errors:**
   - Check write permissions
   - Handle disk space issues
   - Verify output paths

---

## Performance Considerations

- Should process table in under 5 seconds
- Memory efficient for large tables (1000+ rows)
- Scalable to multiple images
- Minimal dependency footprint

---

## Testing Checklist

- [ ] Extract all columns correctly
- [ ] Preserve all data values
- [ ] Generate valid CSV files
- [ ] Print formatted tables
- [ ] Identify "oneview_triagex_failed" labels
- [ ] Identify "oneview_triagex_success" labels
- [ ] Create correct hyperlinks
- [ ] Generate HTML with working links
- [ ] Handle rows with no matching labels
- [ ] Display summary statistics

---

## Usage Example

```bash
# Install dependencies
pip install -r requirements.txt

# Run the program
python jira_table_processor.py

# Expected output files:
# - jira_table.csv
# - jira_status_report.csv
# - jira_status_report.html

# View HTML report in browser
open jira_status_report.html  # macOS
xdg-open jira_status_report.html  # Linux
start jira_status_report.html  # Windows
```

---

## Customization Options

### 1. Change Output Paths
```python
processor.save_to_csv(df, '/custom/path/output.csv')
```

### 2. Add More Label Checks
```python
if 'custom_label' in labels:
    status = 'Custom Status'
```

### 3. Modify Link Format
```python
base_url = "https://custom-jira.com/browse/"
link = f"{base_url}{key}"
```

### 4. Change Report Styling
Modify the CSS in `create_html_report()` function

---

## Success Criteria

✅ Program extracts complete table from image
✅ All data preserved without modification
✅ Original table printed in readable format
✅ Labels analyzed correctly for each row
✅ Status report generated with correct hyperlinks
✅ Multiple output formats created (CSV, HTML)
✅ Final report printed to console
✅ All files saved to specified locations
✅ Code is modular and reusable
✅ Documentation is clear and comprehensive

---

## End Result

A complete, professional Python solution that:
1. Converts JIRA screenshot to structured data
2. Analyzes ticket labels automatically
3. Generates comprehensive status reports
4. Provides multiple output formats
5. Creates clickable links for easy navigation
6. Presents data in clear, readable formats
7. Can be easily integrated into workflows
8. Is maintainable and extensible

---

*This prompt can be used to recreate the entire JIRA table processing system from scratch.*
