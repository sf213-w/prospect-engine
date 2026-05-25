import csv
import os
import re
import time

from datetime import datetime
from playwright.sync_api import sync_playwright


# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------

URL = "https://ocrportal.hhs.gov/ocr/breach/breach_report_hip.jsf"

RAW_CSV = "hhs_breach_report.csv"
FILTERED_CSV = "filtered_hhs_breaches.csv"

TARGET_MONTHS = {"2026-04", "2026-05"}

HEADLESS = True


# -------------------------------------------------------------------
# COLUMN INDICES (FIXED ASSUMPTION FROM YOUR PIPELINE)
# -------------------------------------------------------------------

COL_NAME = 0
COL_ENTITY_TYPE = 2
COL_BREACH_DATE = 3
COL_BREACH_TYPE = 4
COL_RECORDS = 5
COL_CITY = 6
COL_STATE = 7


# -------------------------------------------------------------------
# STATE MAP (kept for downstream correctness)
# -------------------------------------------------------------------

STATE_MAP = {
	"01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
	"08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
	"13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
	"19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
	"24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
	"29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
	"34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
	"39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
	"45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
	"50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
	"56": "WY"
}


# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def normalize_state(state):
	if not state:
		return ""

	state = state.strip()

	if len(state) == 2 and state.isalpha():
		return state.upper()

	state = state.zfill(2)
	return STATE_MAP.get(state, "")


def breach_in_target_period(date_str):
	try:
		dt = datetime.strptime(date_str, "%m/%d/%Y")
		return dt.strftime("%Y-%m") in TARGET_MONTHS
	except:
		return False


# -------------------------------------------------------------------
# WORKING DOWNLOADER (REPLACED WITH YOUR STABLE VERSION)
# -------------------------------------------------------------------

def _find_export_button(page):
	selectors = [
		'a[title*="csv" i]',
		'a[title*="export" i]',
		'button[title*="csv" i]',
		'button[title*="export" i]',
		'a:has-text("CSV")',
		'a:has-text("Export")',
		'button:has-text("CSV")',
		'button:has-text("Export")',
		'a[id*="csv" i]',
		'a[id*="export" i]',
		'span[title*="csv" i]',
		'span[title*="export" i]',
		'a img[src*="csv"]',
		'a img[src*="export"]',
		'.ui-icon-arrowthickstop-1-s',
	]

	for sel in selectors:
		try:
			el = page.locator(sel).first
			if el.count() > 0 and el.is_visible():
				print(f"Found export button: {sel}")
				return el
		except:
			continue

	return None


def download_hhs_csv(download_path=RAW_CSV):
	with sync_playwright() as p:
		browser = p.chromium.launch(headless=HEADLESS)
		context = browser.new_context(accept_downloads=True)
		page = context.new_page()

		print("Loading HHS portal...")
		page.goto(URL, timeout=60000)

		print("Waiting for table...")
		page.wait_for_selector("tbody tr", timeout=30000)

		for _ in range(10):
			rows = page.query_selector_all("tbody tr")
			if rows and rows[0].inner_text().strip():
				break
			time.sleep(1)

		print("Locating export button...")
		btn = _find_export_button(page)

		if not btn:
			page.screenshot(path="debug_no_export.png")
			raise RuntimeError("Export button not found")

		# -----------------------------
		# TRY DOWNLOAD EVENT
		# -----------------------------
		print("Attempting download...")

		try:
			with page.expect_download(timeout=15000) as dl:
				btn.click()

			download = dl.value
			download.save_as(download_path)

			print(f"Saved CSV -> {download_path}")
			return download_path

		except Exception:
			print("No download event — trying response fallback...")

		# -----------------------------
		# FALLBACK: RESPONSE CAPTURE
		# -----------------------------
		csv_data = None

		def handle_response(response):
			nonlocal csv_data
			try:
				if "csv" in response.headers.get("content-type", "").lower():
					csv_data = response.body()
			except:
				pass

		page.on("response", handle_response)

		btn.click()
		page.wait_for_timeout(8000)

		if csv_data:
			with open(download_path, "wb") as f:
				f.write(csv_data)

			print(f"Saved via response -> {download_path}")
			return download_path

		page.screenshot(path="debug_no_csv_response.png")
		raise RuntimeError("CSV download failed")


# -------------------------------------------------------------------
# FILTER
# -------------------------------------------------------------------

def filter_breaches():
	seen = set()

	output_fields = [
		"organization_name",
		"organization_normalized",
		"entity_type",
		"city",
		"state",
		"breach_date",
		"breach_month",
		"breach_type",
		"records_affected",
	]

	with open(RAW_CSV, newline="", encoding="utf-8-sig") as infile, \
		 open(FILTERED_CSV, "w", newline="", encoding="utf-8") as outfile:

		reader = csv.reader(infile)
		writer = csv.DictWriter(outfile, fieldnames=output_fields)
		writer.writeheader()

		next(reader, None)

		for row in reader:
			try:
				name = row[COL_NAME].strip()
				entity_type = row[COL_ENTITY_TYPE].strip()
				raw_state = row[COL_STATE].strip()
				breach_date = row[COL_BREACH_DATE].strip()
				breach_type = row[COL_BREACH_TYPE].strip()
				records = row[COL_RECORDS].strip()
				city = row[COL_CITY].strip()
			except:
				continue

			if not breach_in_target_period(breach_date):
				continue

			if "Healthcare Provider" not in entity_type:
				continue

			state = normalize_state(raw_state)

			norm = name.lower().replace(" ", "")

			if norm in seen:
				continue

			seen.add(norm)

			try:
				breach_month = datetime.strptime(
					breach_date, "%m/%d/%Y"
				).strftime("%Y-%m")
			except:
				breach_month = ""

			writer.writerow({
				"organization_name": name,
				"organization_normalized": norm,
				"entity_type": entity_type,
				"city": city,
				"state": state,
				"breach_date": breach_date,
				"breach_month": breach_month,
				"breach_type": breach_type,
				"records_affected": records,
			})

			print(f"{breach_date} | {name} | {state}")


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

if __name__ == "__main__":
	print("Starting HHS breach downloader...\n")

	if not os.path.exists(RAW_CSV):
		download_hhs_csv()
	else:
		print(f"Using existing CSV -> {RAW_CSV}")

	filter_breaches()
	print("\nPipeline complete.\n")