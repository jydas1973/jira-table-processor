# Installation Guide - JIRA Table Processor

## Prerequisites

- **Python**: Version 3.8 or higher
- **pip**: Python package installer (usually comes with Python)

## Installation Steps

### Option 1: Using requirements.txt (Recommended)

```bash
# Install all dependencies at once
pip install -r requirements.txt
```

### Option 2: Manual Installation

```bash
# Install dependencies one by one
pip install pandas>=2.0.0
pip install Pillow>=10.0.0
pip install opencv-python>=4.8.0
pip install openpyxl>=3.1.0
```

### Option 3: For Linux/Oracle Cloud (with --break-system-packages)

If you're working on Oracle Linux or similar systems where you might encounter system package conflicts:

```bash
pip install pandas Pillow opencv-python openpyxl --break-system-packages
```

## Verifying Installation

After installation, verify that all packages are installed correctly:

```bash
python3 -c "import pandas; import PIL; import cv2; print('All packages installed successfully!')"
```

## Running the Program

```bash
# Make sure you're in the correct directory
cd /path/to/your/project

# Run the program
python jira_table_processor.py
```

## Package Details

### Required Packages:

1. **pandas (>=2.0.0)**
   - Purpose: Data manipulation and CSV handling
   - Used for: Creating and managing DataFrames, exporting to CSV

2. **Pillow (>=10.0.0)**
   - Purpose: Image processing
   - Used for: Loading and basic image operations

3. **opencv-python (>=4.8.0)**
   - Purpose: Advanced image processing
   - Used for: Reading image files

4. **openpyxl (>=3.1.0)**
   - Purpose: Excel file support
   - Used for: Optional Excel export functionality

### Optional Packages:

- **pytesseract**: Only needed if you want to add OCR functionality for automated text extraction

## Troubleshooting

### Issue: "No module named 'cv2'"
**Solution:**
```bash
pip install opencv-python
```

### Issue: "No module named 'PIL'"
**Solution:**
```bash
pip install Pillow
```

### Issue: Permission denied during installation
**Solution:**
```bash
# Use --user flag
pip install -r requirements.txt --user

# OR use sudo (Linux/Mac)
sudo pip install -r requirements.txt

# OR use virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Issue: "WARNING: The directory '/home/user/.cache/pip' is not owned..."
**Solution:**
```bash
pip install -r requirements.txt --break-system-packages
```

## Virtual Environment Setup (Recommended)

Using a virtual environment keeps your project dependencies isolated:

```bash
# Create virtual environment
python3 -m venv jira_processor_env

# Activate virtual environment
# On Linux/Mac:
source jira_processor_env/bin/activate

# On Windows:
jira_processor_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the program
python jira_table_processor.py

# Deactivate when done
deactivate
```

## Minimum System Requirements

- **RAM**: 2GB minimum (4GB recommended)
- **Disk Space**: 500MB for Python packages
- **OS**: Windows 10+, Linux (any modern distro), macOS 10.13+

## Quick Start Command (All-in-One)

```bash
# Clone/download the project, install dependencies, and run
pip install -r requirements.txt && python jira_table_processor.py
```

## Checking Package Versions

```bash
# Check installed versions
pip list | grep -E "pandas|Pillow|opencv|openpyxl"

# Or check specific package
pip show pandas
```

## Upgrading Packages

```bash
# Upgrade all packages to latest versions
pip install --upgrade pandas Pillow opencv-python openpyxl

# Or upgrade from requirements file
pip install --upgrade -r requirements.txt
```

## For Production/Server Deployment

```bash
# Create a frozen requirements file with exact versions
pip freeze > requirements_frozen.txt

# This ensures reproducible installations
pip install -r requirements_frozen.txt
```

## Support

If you encounter any issues during installation:
1. Check Python version: `python --version` (should be 3.8+)
2. Check pip version: `pip --version`
3. Try upgrading pip: `pip install --upgrade pip`
4. Check system logs for detailed error messages
