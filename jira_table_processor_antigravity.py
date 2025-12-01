import cv2
import pytesseract
import pandas as pd
import numpy as np
from PIL import Image
import os
from typing import Tuple, List, Optional

# Set tesseract cmd if needed (usually in PATH)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class JiraTableProcessor:
    def __init__(self, image_path: str):
        self.image_path = image_path
        self.df = pd.DataFrame()
        self.status_df = pd.DataFrame()

    def extract_table_from_image(self) -> pd.DataFrame:
        """
        Extracts a table from a JIRA screenshot and returns a DataFrame.
        """
        print(f"Processing image: {self.image_path}")
        
        if not os.path.exists(self.image_path):
            print(f"Error: File not found at {self.image_path}")
            return pd.DataFrame()

        # 1. Load image
        img = cv2.imread(self.image_path)
        if img is None:
            print("Error: Could not read image.")
            return pd.DataFrame()

        # 2. Preprocessing
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 3. OCR with data extraction
        custom_config = r'--oem 3 --psm 6' 
        data = pytesseract.image_to_data(thresh, config=custom_config, output_type=pytesseract.Output.DICT)
        
        # 4. Parse OCR data
        n_boxes = len(data['text'])
        rows = []
        
        for i in range(n_boxes):
            text = data['text'][i].strip()
            if not text:
                continue
            
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            rows.append({'text': text, 'x': x, 'y': y, 'w': w, 'h': h})
            
        if not rows:
            print("No text detected.")
            return pd.DataFrame()

        df_words = pd.DataFrame(rows)
        
        # 5. Group by Rows
        df_words = df_words.sort_values(by='y')
        row_groups = []
        current_row_y = -100
        row_tolerance = 15 
        current_row_index = -1
        row_indices = []
        
        for index, row in df_words.iterrows():
            if abs(row['y'] - current_row_y) > row_tolerance:
                current_row_index += 1
                current_row_y = row['y']
            row_indices.append(current_row_index)
            
        df_words['row_index'] = row_indices
        
        # 6. Reconstruct Table
        table_rows = []
        unique_rows = df_words['row_index'].unique()
        
        for r_idx in unique_rows:
            row_data = df_words[df_words['row_index'] == r_idx].sort_values(by='x')
            
            # Detect column gaps
            row_data['x_end'] = row_data['x'] + row_data['w']
            row_data['next_x'] = row_data['x'].shift(-1)
            row_data['gap'] = row_data['next_x'] - row_data['x_end']
            
            column_gap_threshold = 40 
            
            current_cell_text = []
            row_cells = []
            
            for idx, word_row in row_data.iterrows():
                current_cell_text.append(word_row['text'])
                
                if np.isnan(word_row['gap']) or word_row['gap'] > column_gap_threshold:
                    row_cells.append(" ".join(current_cell_text))
                    current_cell_text = []
            
            table_rows.append(row_cells)

        # Normalize table width
        max_cols = max([len(r) for r in table_rows]) if table_rows else 0
        print(f"Detected {len(table_rows)} rows and max {max_cols} columns.")
        
        padded_rows = []
        for r in table_rows:
            if len(r) < max_cols:
                r.extend([''] * (max_cols - len(r)))
            padded_rows.append(r)
            
        if padded_rows:
            # Heuristic: First row is header
            headers = padded_rows[0]
            # Clean headers
            headers = [h.replace('|', '').strip() for h in headers]
            
            self.df = pd.DataFrame(padded_rows[1:], columns=headers)
            return self.df
        else:
            return pd.DataFrame()

    def save_to_csv(self, df: pd.DataFrame, output_path: str) -> str:
        df.to_csv(output_path, index=False)
        print(f"Saved original table to {output_path}")
        return output_path

    def print_table(self, df: pd.DataFrame) -> None:
        print("=" * 80)
        print("ORIGINAL JIRA TABLE")
        print("=" * 80)
        print(df.to_string(index=False))
        print("=" * 80)

    def process_labels_and_create_status_report(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Analyzes labels to determine status and creates a summary report.
        Handles multi-line rows by aggregating text between detected Keys.
        """
        report_data = []
        
        # Identify columns
        key_col = next((c for c in df.columns if 'key' in c.lower() or 'Key' in c), None)
        # We will search for labels in ALL columns because OCR might shift text
        
        if not key_col:
            if len(df.columns) >= 1:
                key_col = df.columns[0]
                print(f"Fallback: Using '{key_col}' as Key column.")
            else:
                return pd.DataFrame()

        import re
        
        current_key = None
        current_labels_text = ""
        
        # Iterate through all rows to aggregate data for each JIRA item
        for index, row in df.iterrows():
            # Check if this row has a new Key
            row_text = " ".join([str(val) for val in row.values if pd.notna(val)])
            
            # Look for a JIRA key pattern (e.g., DBAASOPS-123456)
            # The pattern might be messy like "© = DBAASOPS-465465"
            key_match = re.search(r'([A-Z]+-\d+)', str(row[key_col]))
            
            if key_match:
                # Found a new key, process the PREVIOUS one
                if current_key:
                    status = None
                    # Use regex to be flexible with OCR errors (space vs underscore)
                    if re.search(r'oneview_triagex[ _]failed', current_labels_text):
                        status = "Failed"
                    elif re.search(r'oneview_triagex[ _]success', current_labels_text):
                        status = "Success"
                    
                    if status:
                        link = f"https://jira-sd.mc1.oracleiaas.com/browse/{current_key}"
                        report_data.append({
                            "JIRA ID": current_key,
                            "Status": status,
                            "Link": link
                        })
                
                # Start new item
                current_key = key_match.group(1)
                current_labels_text = row_text # Start accumulating text from this row
            else:
                # Continuation of previous item
                if current_key:
                    current_labels_text += " " + row_text

        # Process the last item
        if current_key:
            status = None
            # Use regex to be flexible with OCR errors (space vs underscore)
            if re.search(r'oneview_triagex[ _]failed', current_labels_text):
                status = "Failed"
            elif re.search(r'oneview_triagex[ _]success', current_labels_text):
                status = "Success"
            
            if status:
                link = f"https://jira-sd.mc1.oracleiaas.com/browse/{current_key}"
                report_data.append({
                    "JIRA ID": current_key,
                    "Status": status,
                    "Link": link
                })
        
        self.status_df = pd.DataFrame(report_data)
        return self.status_df

    def print_status_report(self, status_df: pd.DataFrame) -> None:
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
            print("No matching issues found.")

    def save_status_report_to_csv(self, status_df: pd.DataFrame, output_path: str) -> str:
        status_df.to_csv(output_path, index=False)
        print(f"Saved status report to {output_path}")
        return output_path

    def create_html_report(self, status_df: pd.DataFrame, output_path: str) -> str:
        if status_df.empty:
            html_content = "<html><body><h1>No Data Found</h1></body></html>"
        else:
            # Calculate stats
            total = len(status_df)
            success = len(status_df[status_df['Status'] == 'Success'])
            failed = len(status_df[status_df['Status'] == 'Failed'])
            
            rows_html = ""
            for _, row in status_df.iterrows():
                color = "#d4edda" if row['Status'] == 'Success' else "#f8d7da"
                text_color = "#155724" if row['Status'] == 'Success' else "#721c24"
                rows_html += f"""
                <tr style="background-color: {color}; color: {text_color};">
                    <td style="padding: 10px; border: 1px solid #ddd;">{row['JIRA ID']}</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{row['Status']}</td>
                    <td style="padding: 10px; border: 1px solid #ddd;"><a href="{row['Link']}">{row['Link']}</a></td>
                </tr>
                """

            html_content = f"""
            <html>
            <head>
                <title>JIRA Status Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th {{ background-color: #f2f2f2; padding: 10px; border: 1px solid #ddd; text-align: left; }}
                    .summary {{ margin-top: 20px; padding: 15px; background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <h1>JIRA Status Report</h1>
                <table>
                    <thead>
                        <tr>
                            <th>JIRA ID</th>
                            <th>Status</th>
                            <th>Link</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
                
                <div class="summary">
                    <h3>Summary</h3>
                    <p><strong>Total Issues:</strong> {total}</p>
                    <p><strong>Success:</strong> {success}</p>
                    <p><strong>Failed:</strong> {failed}</p>
                </div>
            </body>
            </html>
            """
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"Saved HTML report to {output_path}")
        return output_path

    def run(self):
        # 1. Extract table from image
        self.df = self.extract_table_from_image()
        
        if self.df.empty:
            print("Extraction failed or empty table.")
            return

        # 2. Save original data to CSV
        self.save_to_csv(self.df, 'jira_table.csv')
        
        # 3. Print original table
        self.print_table(self.df)
        
        # 4. Process labels and create status report
        self.status_df = self.process_labels_and_create_status_report(self.df)
        
        # 5. Save status report to CSV
        self.save_status_report_to_csv(self.status_df, 'jira_status_report.csv')
        
        # 6. Create HTML report with hyperlinks
        self.create_html_report(self.status_df, 'jira_status_report.html')
        
        # 7. Print final status report
        self.print_status_report(self.status_df)

def main():
    image_path = "Screenshot_Nov_25.jpg"
    processor = JiraTableProcessor(image_path)
    processor.run()

if __name__ == "__main__":
    main()
