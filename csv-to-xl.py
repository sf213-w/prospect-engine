"""
Convert CSV files to Excel spreadsheets.
"""

import pandas as pd
import sys
import os
from pathlib import Path


def csv_to_excel(csv_file, output_file=None, sheet_name="Sheet1"):
    """
    Convert a CSV file to an Excel spreadsheet.
    
    Args:
        csv_file (str): Path to the input CSV file
        output_file (str): Path to the output Excel file. If None, uses the same name with .xlsx
        sheet_name (str): Name for the Excel sheet (default: "Sheet1")
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Validate input file exists
        if not os.path.exists(csv_file):
            print(f"Error: Input file '{csv_file}' not found.")
            return False
        
        # Read CSV file
        df = pd.read_csv(csv_file, dtype=str)
        
        # Determine output filename if not specified
        if output_file is None:
            output_file = Path(csv_file).stem + ".xlsx"
        
        # Write to Excel
        df.to_excel(output_file, sheet_name=sheet_name, index=False)
        
        print(f"✓ Successfully converted '{csv_file}' to '{output_file}'")
        print(f"  - Rows: {len(df)}")
        print(f"  - Columns: {len(df.columns)}")
        
        return True
    
    except Exception as e:
        print(f"Error converting file: {e}")
        return False


def main():
    """Main function to handle command-line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python csv-to-xl.py <csv_file> [output_file] [sheet_name]")
        print("\nExample:")
        print("  python csv-to-xl.py data.csv")
        print("  python csv-to-xl.py data.csv output.xlsx")
        print("  python csv-to-xl.py data.csv output.xlsx 'My Sheet'")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    sheet_name = sys.argv[3] if len(sys.argv) > 3 else "Sheet1"
    
    csv_to_excel(csv_file, output_file, sheet_name)


if __name__ == "__main__":
    main()
