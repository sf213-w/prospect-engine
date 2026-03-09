# Data Enrichment Script

This repository contains a Python utility (`data_enrichment.py`) designed to process CSV exports containing prospect/person records. The script enriches the data by adding additional columns such as location, organization type, website, and lead scoring based on email domains, phone numbers, and other available information.

## Files

- `data_enrichment.py` - Main Python module with the `DataEnricher` class and CLI wrapper.
- `data/people-11381378-107.csv` - Sample CSV file used for development and testing.

## Requirements

- Python 3.8 or later
- `pandas` library (install via `pip install pandas`)
- `openpyxl` library (install via `pip install openpyxl`) - required for Excel operations

## Installation

1. Clone or copy the project into your workspace.
2. (Optional) Set up a virtual environment and activate it:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1  # Windows PowerShell
   ```
3. Install required packages:
   ```powershell
   pip install pandas openpyxl
   ```

## Usage

### Command-Line Interface

The script provides three main commands for processing data:

#### 1. Generate Enriched CSV
```powershell
python data_enrichment.py csv <input_csv> <output_csv>
```
- Reads the input CSV file
- Adds enrichment columns to the data
- Saves the enriched data to a new CSV file

#### 2. Generate Enriched Excel File
```powershell
python data_enrichment.py xlsx <input_csv> <output_xlsx>
```
- Reads the input CSV file
- Adds enrichment columns to the data
- Saves the enriched data to a new Excel file

#### 3. Update Existing Excel File
```powershell
python data_enrichment.py update <input_csv> <excel_file>
```
- Reads the input CSV file
- Adds enrichment columns to the data
- Updates an existing Excel file with the enriched data (replaces data rows, keeps headers)

### Programmatic Usage

You can also import and use the script in your own Python code:

```python
from data_enrichment import DataEnricher, process_csv

# Process an entire CSV file
enricher = DataEnricher()
df = pd.read_csv('data/people-11381378-107.csv')
enriched_df = enricher.add_enrichment_columns(df)

# Or use the convenience function
process_csv('input.csv', 'output.csv')

# Use individual methods for single records
enricher = DataEnricher()
info = enricher.extrapolate_location_and_domain("john.doe@company.com", "415-555-1234")
print(info)
```

## Core Functionality

The script performs data enrichment by adding the following columns to your CSV/Excel data:

1. **Email Domain** - Extracts the domain from email addresses
2. **Free Email** - Boolean indicating if the email is from a free provider (gmail.com, yahoo.com, etc.)
3. **Phone Area Code** - Extracts the 3-digit area code from phone numbers
4. **Company Domain** - Infers the company domain from email (excluding free email providers)
5. **Country** - Determines country based on email domain TLD
6. **US Status** - Determines if the record is US-based (US, Non-US, or US Likely)
7. **Location** - Extracts state information for US records
8. **Organization Type** - Categorizes the organization (Corporate, Education, Healthcare, Government, Non-Profit, Personal, Other)
9. **Website** - Infers or copies website information
10. **Lead Type** - Classifies as Business or Personal
11. **Lead Score** - Numeric score based on data quality and business indicators

## Data Format Requirements

The input CSV should contain columns with the following names (case-sensitive):
- `Person - Email - Work`
- `Person - Email - Home`
- `Person - Email - Other`
- `Person - Phone - Work`
- `Person - Phone - Home`
- `Person - State`
- `Person - CompanyName`
- `Person - Website`

## Customization

You can extend the `DataEnricher` class by modifying its constants:
- `FREE_EMAIL_DOMAINS` - Add more free email providers
- `DOMAIN_ORG_TYPES` - Add mappings for organization type detection
- `COUNTRY_TLDS` - Add more country TLD mappings
- `US_STATES` - Update US state abbreviations

## Example Output

After processing, your data will have additional columns like:

```
Email Domain,Free Email,Phone Area Code,Company Domain,Country,US Status,Location,Organization Type,Website,Lead Type,Lead Score
example.com,False,415,example.com,United States,US,CA,Corporate,https://www.example.com,Business,9
gmail.com,True,,,Undetermined,US Likely,,Personal,,Personal,0
```

## Notes

- The script uses pandas for data processing, so ensure you have sufficient memory for large files
- All enrichment is based on heuristics and available data; results may not be 100% accurate
- The script handles missing values gracefully by using "Undetermined" as a default
- For Excel operations, the script requires the `openpyxl` library

## Troubleshooting

- **Import Errors**: Ensure all required packages are installed (`pip install pandas openpyxl`)
- **File Not Found**: Check that input file paths are correct and files exist
- **Memory Issues**: For very large CSV files, consider processing in chunks or using a machine with more RAM
- **Unexpected Results**: Review the input data format to ensure column names match expectations