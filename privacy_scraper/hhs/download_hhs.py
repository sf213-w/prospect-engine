import os
import time
from playwright.sync_api import sync_playwright

from config import HHS_URL, HEADLESS


EXPORT_PATH = "cache/hhs_breach_report.csv"


def download_hhs_csv():
	if os.path.exists(EXPORT_PATH):
		age_hours = (time.time() - os.path.getmtime(EXPORT_PATH)) / 3600

		if age_hours < 24:
			return EXPORT_PATH

	with sync_playwright() as p:
		browser = p.chromium.launch(headless=HEADLESS)
		context = browser.new_context(accept_downloads=True)
		page = context.new_page()

		page.goto(HHS_URL, timeout=60000)
		page.wait_for_selector("tbody tr")

		with page.expect_download(timeout=60000) as download_info:
			page.click('a[title="Export as CSV"]')

		download = download_info.value
		download.save_as(EXPORT_PATH)

		browser.close()

	return EXPORT_PATH