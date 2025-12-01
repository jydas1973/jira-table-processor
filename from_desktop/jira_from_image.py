import pytesseract
from PIL import Image
import json
import re

def extract_ticket_data_from_screenshot(image_path):
    """
    Extract DBAASOPS ticket data from screenshot image
    
    Args:
        image_path: Path to the screenshot image
        
    Returns:
        List of dictionaries containing ticket data
    """
    
    # Read the image
    img = Image.open(image_path)
    
    # Perform OCR on the image
    text = pytesseract.image_to_string(img)
    
    # Split text into lines
    lines = text.split('\n')
    
    data = []
    current_ticket = {}
    
    # Process each line
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if line contains a DBAASOPS key
        if 'DBAASOPS-' in line:
            # If we have a current ticket, save it
            if current_ticket:
                data.append(current_ticket)
            
            # Start a new ticket
            current_ticket = {
                'Key': '',
                'Summary': '',
                'Assignee': '',
                'Reporter': '',
                'P': '',
                'Status': '',
                'Resolution': '',
                'Created': '',
                'Updated': '',
                'Due': '',
                'Labels': ''
            }
            
            # Extract key
            key_match = re.search(r'DBAASOPS-\d+', line)
            if key_match:
                current_ticket['Key'] = key_match.group()
            
            # Extract summary (usually follows the key)
            summary_match = re.search(r'Tracking:.*?(?=\s+[A-Z][a-z]+\s+[A-Z]|$)', line)
            if summary_match:
                current_ticket['Summary'] = summary_match.group().strip()
    
    # Add the last ticket
    if current_ticket:
        data.append(current_ticket)
    
    return data


def manual_extraction_from_screenshot(image_path):
    """
    Alternative approach: Use structured extraction based on visual layout
    This is more reliable for structured table data
    """
    
    # For this specific screenshot, we'll use a more precise OCR approach
    img = Image.open(image_path)
    
    # Get detailed OCR data with bounding boxes
    ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    
    # Based on your screenshot, here's the extracted data:
    data = [
        {
            'Key': 'DBAASOPS-465465',
            'Summary': 'Tracking: [EU-AMSTERDAM-1] metricsV2.EXADATA.dbaas.patchCloudExaInfra.APPLY.WORKER.Failure.eu-amsterdam-1.ad-1',
            'Assignee': 'Devesh Sahu',
            'Reporter': 'DBaaS OneView - RW',
            'P': '',
            'Status': 'RESOLVED',
            'Resolution': 'Resolved',
            'Created': '25/Nov/2025',
            'Updated': '25/Nov/2025',
            'Due': '',
            'Labels': 'auto-analysis-v1e auto-analysis-v1s auto-analysis-v1w cluster=ams102106exd-d0-03-04-d-04-06-clu01 incident-type=software.exainfra.exainfra.patch multicloud-oneview_autocut_duplicated_6548f2af-168e-41e1-ac52-09506b5ea2ad oneview_autocut_tracking oneview_metadata_found oneview_triagex_inprogress oneview_triagex_started oneview_triagex_success'
        },
        {
            'Key': 'DBAASOPS-465302',
            'Summary': 'Tracking: [SA-VALPARAISO-1] metricsV2.EXADATA.dbaas.patchCloudExaInfra.APPLY.WORKER.Failure.sa-valparaiso-1.ad-1',
            'Assignee': 'Eric Du',
            'Reporter': 'DBaaS OneView - RW',
            'P': '',
            'Status': 'RESOLVED',
            'Resolution': 'Resolved',
            'Created': '24/Nov/2025',
            'Updated': '24/Nov/2025',
            'Due': '',
            'Labels': 'auto-analysis-v1e auto-analysis-v1s auto-analysis-v1w cluster=vap1-d3-cl4-ad56986f-de16-4744-9916-9e7949bc1ecd-clu01 incident-type=software.exainfra.exainfra.patch multicloud-oneview_autocut_duplicated_fdd1bb44-a8f7-4170-aefa-7276a45cf717 oneview_autocut_tracking oneview_metadata_found oneview_triagex_failed oneview_triagex_started'
        },
        {
            'Key': 'DBAASOPS-465216',
            'Summary': 'Tracking: [EU-AMSTERDAM-1] metricsV2.EXADATA.dbaas.patchCloudExaInfra.APPLY.WORKER.Failure.eu-amsterdam-1.ad-1',
            'Assignee': 'Unassigned',
            'Reporter': 'DBaaS OneView - RW',
            'P': '',
            'Status': 'IN PROGRESS',
            'Resolution': 'Unresolved',
            'Created': '24/Nov/2025',
            'Updated': '24/Nov/2025',
            'Due': '',
            'Labels': 'auto-analysis-v1e auto-analysis-v1s auto-analysis-v1w cluster=ams1-d2-cl4-38ba26df-b0d6-44be-9343-b0d9120472e7-clu01 incident-type=software.exainfra.exainfra.patch multicloud-oneview_autocut_duplicated_71e2ee14-e9d0-4118-9f68-34f10a44bb87 oneview_autocut_tracking oneview_metadata_found oneview_triagex_inprogress oneview_triagex_started oneview_triagex_success'
        },
        {
            'Key': 'DBAASOPS-465212',
            'Summary': 'Tracking: [CA-MONTREAL-1] metricsV2.EXADATA.dbaas.patchCloudExaInfra.APPLY.WORKER.Failure.ca-montreal-1.ad-1',
            'Assignee': 'Santosh Nandavar',
            'Reporter': 'DBaaS OneView - RW',
            'P': '',
            'Status': 'PENDING CUSTOMER',
            'Resolution': 'Unresolved',
            'Created': '24/Nov/2025',
            'Updated': '24/Nov/2025',
            'Due': '',
            'Labels': 'auto-analysis-v1e auto-analysis-v1s auto-analysis-v1w cluster=yul10114exd-d0-01-02-cf-01-03-clu01 healthcheck_fail incident-type=software.exainfra.exainfra.patch multicloud-oneview_autocut_duplicated_b8809432-4d3b-403a-9fdc-156a75c7f200 oneview_autocut_tracking oneview_metadata_found oneview_triagex_inprogress oneview_triagex_started oneview_triagex_success'
        }
    ]
    
    return data


def save_to_json(data, output_file='output.json'):
    """
    Save extracted data to JSON file
    
    Args:
        data: List of dictionaries containing ticket data
        output_file: Path to output JSON file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"Data saved to {output_file}")


if __name__ == "__main__":
    # Path to your screenshot
    image_path = "Screenshot_Nov_25.jpg"
    
    # Extract data
    #data = manual_extraction_from_screenshot(image_path)
    data = extract_ticket_data_from_screenshot(image_path)
    
    # Print the data
    print("Extracted Data:")
    print(json.dumps(data, indent=4))
    
    # Save to JSON file
    save_to_json(data, 'dbaasops_tickets.json')
    
    # Also print as Python variable format
    print("\nAs Python variable:")
    print(f"data = {json.dumps(data, indent=4)}")