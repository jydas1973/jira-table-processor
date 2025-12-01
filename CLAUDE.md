# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a JIRA table image processing system that extracts tabular data from JIRA screenshots, analyzes labels to determine status (success/failed), and generates comprehensive reports in multiple formats (CSV, HTML).

## Common Commands

### Installation
```bash
# Install all dependencies
pip install -r requirements.txt

# On Oracle Linux or systems with package conflicts
pip install -r requirements.txt --break-system-packages

# Using virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Running the Application
```bash
# Main processor (OCR-based extraction)
python jira_table_processor.py

# Alternative processor (antigravity variant)
python jira_table_processor_antigravity.py

# Desktop version (manual data extraction)
python from_desktop/jira_table_processor_desktop.py
```

### Windows-Specific Setup
The main processor requires Tesseract OCR on Windows. Set the path in the code:
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

## Architecture

### Core Class: `JiraTableProcessor`

The application is built around a single class that handles the complete workflow:

1. **Image Input**: Takes a JIRA screenshot (default: `Screenshot_Nov_25.jpg`)
2. **Table Extraction**: Uses OCR (pytesseract) and image processing (OpenCV) to extract table data
3. **Label Analysis**: Searches for specific labels to determine status:
   - `oneview_triagex_success` → Status: "Success"
   - `oneview_triagex_failed` → Status: "Failed"
4. **Report Generation**: Creates outputs in multiple formats

### Implementation Variants

There are three main implementations with different extraction strategies:

#### 1. `jira_table_processor.py` (Main - OCR with Contour Detection)
- Uses OpenCV to detect table structure via contour detection
- Applies morphological operations to find vertical/horizontal lines
- Extracts cells using bounding boxes
- OCR per cell for text extraction
- **Most complex** but attempts fully automated extraction

#### 2. `jira_table_processor_antigravity.py` (OCR with Word Grouping)
- Uses pytesseract's `image_to_data` to get word positions
- Groups words by vertical position (rows)
- Groups words by horizontal gaps (columns)
- Reconstructs table from spatial relationships
- **Middle complexity** - relies on spatial analysis

#### 3. `from_desktop/jira_table_processor_desktop.py` (Manual Data)
- Contains hardcoded table data extracted from the screenshot
- No actual image processing
- **Most reliable** for demonstration/testing
- Used as ground truth for comparing OCR results

### Workflow Methods

All implementations follow this workflow (defined in the `run()` method):

```python
def run(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
    # 1. Extract table from image
    original_df = self.extract_table_from_image()

    # 2. Save original data
    self.save_to_csv(original_df, 'jira_table.csv')

    # 3. Print original table
    self.print_table(original_df)

    # 4. Process labels for status
    status_df = self.process_labels_and_create_status_report(original_df)

    # 5. Save status report
    self.save_status_report_to_csv(status_df, 'jira_status_report.csv')

    # 6. Create HTML report
    self.create_html_report(status_df, 'jira_status_report.html')

    # 7. Print status report
    self.print_status_report(status_df)

    return original_df, status_df
```

### Expected Table Schema

All implementations expect these columns from JIRA:
- Key (JIRA ticket ID, e.g., DBAASOPS-465465)
- Summary
- Assignee
- Reporter
- P (Priority)
- Status
- Resolution
- Created
- Updated
- Due
- Labels (comma/space-separated string)

### Label Processing Logic

The `process_labels_and_create_status_report()` method:
1. Iterates through each row
2. Extracts the Key field
3. Searches Labels field for status indicators
4. Generates hyperlink: `https://jira-sd.mc1.oracleiaas.com/browse/{KEY}`
5. Creates status report with only rows containing success/failed labels
6. Rows without these labels are **excluded** from the status report

### Output Files

The application generates three types of output:

1. **jira_table.csv** - Original extracted data (all columns, all rows)
2. **jira_status_report.csv** - Filtered status report (JIRA ID, Link, Status)
3. **jira_status_report.html** - Styled HTML report with:
   - Clickable JIRA hyperlinks
   - Color-coded status (green for Success, red for Failed)
   - Summary statistics (Total, Success count, Failed count)

### Output Directories

- Root directory: Main processors output here
- `reports/` directory: Used by `jira_table_processor.py` variant
- `from_desktop/` directory: Desktop variant outputs here

## Key Implementation Details

### OCR Challenges

The OCR-based implementations handle several challenges:
- **Multi-line rows**: Labels can span multiple lines; text is accumulated across rows
- **Column misalignment**: OCR may shift text between columns
- **Noise and artifacts**: Image preprocessing with thresholding helps
- **Row grouping**: Tolerance thresholds group words by vertical position

### Regex Pattern Matching

The antigravity variant uses flexible regex for label matching:
```python
# Handles both underscores and spaces (OCR inconsistencies)
re.search(r'oneview_triagex[ _]failed', labels_text)
re.search(r'oneview_triagex[ _]success', labels_text)
```

### JIRA Key Extraction

Pattern: `r'([A-Z]+-\d+)'` matches keys like DBAASOPS-465465

## Development Notes

### Adding New Label Types

To add new label-based statuses, modify `process_labels_and_create_status_report()`:
```python
if 'new_label_pattern' in labels:
    status = 'Custom Status'
    # Add to report_data
```

### Changing JIRA URL

Modify the hyperlink format in `process_labels_and_create_status_report()`:
```python
link = f"https://custom-jira-instance.com/browse/{key}"
```

### Customizing HTML Report

Edit the CSS in `create_html_report()` method. Current styling uses:
- Blue header (#0052CC)
- Green success rows (#d4edda)
- Red failed rows (#f8d7da)

### Adjusting OCR Parameters

For better extraction accuracy, tune these parameters:
- `row_tolerance`: Vertical threshold for grouping words into rows (default: 15)
- `column_gap_threshold`: Horizontal gap to separate columns (default: 40)
- Tesseract config: `--oem 3 --psm 6` (page segmentation mode)

## Reference Documentation

- **COMPREHENSIVE_PROMPT.md**: Complete specification with all requirements and examples
- **from_desktop/INSTALLATION.md**: Detailed installation guide with troubleshooting
- **requirements.txt**: Python dependencies

## Testing

When testing OCR extraction:
1. Compare output against the desktop version (ground truth)
2. Verify all 4 JIRA tickets are extracted
3. Ensure labels are captured completely (they contain critical status info)
4. Check that status report correctly identifies 3 success, 1 failed
