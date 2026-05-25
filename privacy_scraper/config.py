from datetime import datetime

TARGET_COUNT = 100

HHS_URL = "https://ocrportal.hhs.gov/ocr/breach/breach_report_hip.jsf"

REQUEST_TIMEOUT = 15
MAX_PAGES_PER_SITE = 15
HEADLESS = True
CACHE_ENABLED = True

OUTPUT_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

CSV_OUTPUT = f"output/privacy_contacts_{OUTPUT_TIMESTAMP}.csv"
EXCEL_OUTPUT = f"output/privacy_contacts_{OUTPUT_TIMESTAMP}.xlsx"

USER_AGENT = (
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
	"AppleWebKit/537.36"
)