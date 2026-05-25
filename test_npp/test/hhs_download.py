import time
from playwright.sync_api import sync_playwright

URL = "https://ocrportal.hhs.gov/ocr/breach/breach_report_hip.jsf"


# -----------------------------
# FIND EXPORT BUTTON (ROBUST)
# -----------------------------
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
				print(f"  ✅ Found export button: {sel}")
				return el
		except Exception:
			continue

	return None


# -----------------------------
# MAIN DOWNLOAD FUNCTION
# -----------------------------
def download_hhs_csv(download_path="hhs_breach_report.csv"):
	with sync_playwright() as p:
		browser = p.chromium.launch(headless=True)
		context = browser.new_context(accept_downloads=True)
		page = context.new_page()

		print("🌐 Loading HHS portal...")
		page.goto(URL, timeout=60000)

		print("⏳ Waiting for table...")
		page.wait_for_selector("tbody tr", timeout=30000)

		# ensure data is actually populated
		for _ in range(10):
			rows = page.query_selector_all("tbody tr")
			if rows and rows[0].inner_text().strip():
				break
			time.sleep(1)

		print("🔎 Locating export button...")
		btn = _find_export_button(page)

		if not btn:
			page.screenshot(path="debug_no_export.png")
			raise RuntimeError("Export button not found (see debug_no_export.png)")

		# -----------------------------
		# TRY DOWNLOAD EVENT FIRST
		# -----------------------------
		print("⬇️ Attempting download via click...")

		try:
			with page.expect_download(timeout=15000) as dl:
				btn.click()

			download = dl.value
			download.save_as(download_path)

			print(f"✅ Download complete: {download_path}")
			return download_path

		except Exception:
			print("⚠️ No download event detected — trying response capture...")

		# -----------------------------
		# FALLBACK: RESPONSE INTERCEPT
		# (JSF often uses this)
		# -----------------------------
		csv_data = None

		def handle_response(response):
			nonlocal csv_data
			try:
				if "csv" in response.headers.get("content-type", "").lower():
					csv_data = response.body()
			except Exception:
				pass

		page.on("response", handle_response)

		btn.click()
		page.wait_for_timeout(8000)

		if csv_data:
			with open(download_path, "wb") as f:
				f.write(csv_data)
			print(f"✅ Downloaded via response interception: {download_path}")
			return download_path

		page.screenshot(path="debug_no_csv_response.png")
		raise RuntimeError("CSV download failed (see debug_no_csv_response.png)")


if __name__ == "__main__":
	download_hhs_csv()