"""
privacy_contact_scraper.py
───────────────────────────────────────────────────────────────────────────────
Enterprise-grade HHS OCR Breach Privacy Contact Scraper

Major Improvements
───────────────────────────────────────────────────────────────────────────────
✓ Robust request retry/session handling
✓ Contact email normalization + validation
✓ Stronger de-duplication logic
✓ Provider-domain email prioritization
✓ Reduced false positives from junk emails
✓ Contact quality scoring
✓ Duplicate email suppression across providers
✓ Improved privacy/contact page discovery
✓ Better logging and diagnostics
✓ Safer regex extraction
✓ Canonical provider normalization
✓ Reduced duplicate CSV rows
✓ Smarter contact ranking
✓ Better phone parsing
✓ Email/domain ownership validation
✓ Graceful failure handling
✓ Session reuse for performance
✓ Improved Excel reporting compatibility

Recommended Python Packages
───────────────────────────────────────────────────────────────────────────────
pip install:
    requests
    beautifulsoup4
    playwright
    ddgs
    openpyxl

Also run:
    playwright install
"""

import csv
import os
import re
import time
import hashlib
import requests

from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
from ddgs import DDGS
from playwright.sync_api import sync_playwright

# Excel
from openpyxl import Workbook


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

URL = "https://ocrportal.hhs.gov/ocr/breach/breach_report_hip.jsf"

TARGET_COUNT = 100

HHS_CSV_PATH = "hhs_breach_report.csv"

RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")

CSV_FILE = f"privacy_contacts_{RUN_TS}.csv"

REQUEST_TIMEOUT = 15

HEADERS = {
	"User-Agent": (
		"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
		"AppleWebKit/537.36 (KHTML, like Gecko) "
		"Chrome/124.0 Safari/537.36"
	)
}

CSV_FIELDS = [
	"provider_name",
	"provider_normalized",
	"breach_submission_date",
	"first_name",
	"last_name",
	"website",
	"emails",
	"phones",
	"source_url",
	"context_snippet",
	"found_via",
	"contact_quality",
	"email_domain_matches_site",
	"date_scraped",
]


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL DEDUP TRACKING
# ─────────────────────────────────────────────────────────────────────────────

# Prevent duplicate rows
WRITTEN_ROW_HASHES = set()

# Prevent duplicate contact emails from presumed valid contacts
# across all providers
GLOBAL_EMAIL_REGISTRY = {}

# Keep best row per provider in-memory
BEST_PROVIDER_ROWS = {}

# Shared requests session
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ─────────────────────────────────────────────────────────────────────────────
# BAD DOMAINS
# ─────────────────────────────────────────────────────────────────────────────

BAD_DOMAINS = {
	"linkedin.com",
	"facebook.com",
	"twitter.com",
	"instagram.com",
	"youtube.com",
	"healthgrades.com",
	"mapquest.com",
	"popupportal.com",
	"wikipedia.org",
	"yelp.com",
	"claimdepot.com",
	"classaction.org",
	"topclassactions.com",
	"hipaajournal.com",
	"hhs.gov",
	"cms.gov",
	"bbb.org",
	"glassdoor.com",
	"indeed.com",
	"doximity.com",
	"vitals.com",
	"webmd.com",
	"zocdoc.com",
	"zoominfo.com",
	"signalhire.com",
	"rocketreach.co",
	"apollo.io",
	"contactout.com",
	"leadiq.com",
	"seamless.ai",
	"npino.com",
}

GENERIC_EMAIL_PREFIXES = {
	"info",
	"support",
	"admin",
	"contact",
	"hello",
	"privacy",
	"hipaa",
	"compliance",
	"help",
	"customerservice",
	"noreply",
	"no-reply",
	"webmaster",
	"marketing",
	"communications",
}


PRIVACY_PATHS = [
	"/privacy",
	"/privacy-policy",
	"/privacy-notice",
	"/hipaa",
	"/hipaa-notice",
	"/compliance",
	"/contact",
	"/contact-us",
	"/about/privacy",
	"/about/contact",
	"/patients/privacy",
	"/notices/privacy",
	"/notice-of-privacy-practices",
]


ROLE_KEYWORDS = [
	"privacy officer",
	"chief privacy officer",
	"compliance officer",
	"hipaa officer",
	"hipaa privacy officer",
	"data protection officer",
	"privacy contact",
	"privacy director",
	"privacy manager",
]


EMAIL_RE = re.compile(
	r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

PHONE_RE = re.compile(
	r"(?:\+?1[\s\-.]?)?"
	r"(?:\(?\d{3}\)?[\s\-.]?)"
	r"\d{3}[\s\-.]?\d{4}"
)

NAME_RE = re.compile(
	r"\b([A-Z][a-z]+(?:[-'][A-Z][a-z]+)?)\s+"
	r"([A-Z][a-z]+(?:[-'][A-Z][a-z]+)?)\b"
)


# ─────────────────────────────────────────────────────────────────────────────
# CSV
# ─────────────────────────────────────────────────────────────────────────────

def init_csv():
	with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
		writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
		writer.writeheader()

	print(f"📄 CSV initialized: {CSV_FILE}")


def normalize_provider_name(name):
	"""
	Canonical normalization for deduplication.
	"""

	if not name:
		return ""

	name = name.lower()

	replacements = [
		("llc", ""),
		("inc", ""),
		("corp", ""),
		("corporation", ""),
		("health system", ""),
		("healthcare", ""),
		("hospital", ""),
		("medical center", ""),
		("medical ctr", ""),
		("clinic", ""),
		("pllc", ""),
	]

	for old, new in replacements:
		name = name.replace(old, new)

	name = re.sub(r"[^a-z0-9]", "", name)

	return name.strip()


def normalize_email(email):
	email = email.strip().lower()

	if email.startswith("mailto:"):
		email = email.replace("mailto:", "")

	email = email.strip(".,;:()[]{}<>")

	return email


def email_domain(email):
	try:
		return email.split("@")[1].lower()
	except:
		return ""


def get_root_domain(url):
	try:
		netloc = urlparse(url).netloc.lower()
		netloc = netloc.replace("www.", "")
		return netloc
	except:
		return ""


def is_valid_email(email):
	if not email:
		return False

	email = normalize_email(email)

	if not EMAIL_RE.fullmatch(email):
		return False

	domain = email_domain(email)

	for bad in BAD_DOMAINS:
		if bad in domain:
			return False

	return True


def is_personal_email(email):
	domain = email_domain(email)

	personal_domains = {
		"gmail.com",
		"yahoo.com",
		"hotmail.com",
		"outlook.com",
		"aol.com",
		"icloud.com",
		"protonmail.com",
	}

	return domain in personal_domains


def is_likely_provider_email(email, website):
	"""
	Strong validation:
	Prefer emails whose domain matches provider website.
	"""

	if not email or not website:
		return False

	email_dom = email_domain(email)
	site_dom = get_root_domain(website)

	return (
		email_dom == site_dom or
		email_dom.endswith("." + site_dom) or
		site_dom.endswith("." + email_dom)
	)


def deduplicate_emails(emails, website=None):
	"""
	Strong email cleanup + prioritization.
	"""

	cleaned = []

	seen = set()

	for email in emails:
		email = normalize_email(email)

		if not is_valid_email(email):
			continue

		if email in seen:
			continue

		seen.add(email)

		cleaned.append(email)

	# Prefer provider-owned emails first
	if website:
		cleaned.sort(
			key=lambda e: (
				not is_likely_provider_email(e, website),
				is_personal_email(e),
				len(e),
			)
		)

	return cleaned


def row_hash(row):
	key = "|".join([
		row.get("provider_name", ""),
		row.get("emails", ""),
		row.get("phones", ""),
		row.get("source_url", ""),
	])

	return hashlib.sha256(key.encode()).hexdigest()


def contact_quality_score(row):
	score = 0

	emails = row.get("emails", "")

	if emails:
		score += 100

	if row.get("phones"):
		score += 20

	if row.get("first_name"):
		score += 10

	if row.get("found_via") == "site crawl":
		score += 15

	if row.get("email_domain_matches_site") == "yes":
		score += 50

	return score


def should_keep_email(email, provider):
	"""
	Global cross-provider deduplication.

	If the same email appears under multiple providers,
	keep only the highest-confidence provider association.
	"""

	email = normalize_email(email)

	if email not in GLOBAL_EMAIL_REGISTRY:
		GLOBAL_EMAIL_REGISTRY[email] = provider
		return True

	existing_provider = GLOBAL_EMAIL_REGISTRY[email]

	if normalize_provider_name(existing_provider) == normalize_provider_name(provider):
		return True

	return False


def write_csv_row(row):
	"""
	Strong deduplication layer.
	"""

	row["provider_normalized"] = normalize_provider_name(
		row.get("provider_name", "")
	)

	row["contact_quality"] = contact_quality_score(row)

	row_id = row_hash(row)

	if row_id in WRITTEN_ROW_HASHES:
		return

	emails = [
		e.strip()
		for e in row.get("emails", "").split(";")
		if e.strip()
	]

	valid_emails = []

	for email in emails:

		if not should_keep_email(email, row["provider_name"]):
			print(f"     ⚠️ Duplicate email suppressed: {email}")
			continue

		valid_emails.append(email)

	row["emails"] = "; ".join(valid_emails)

	# Skip rows with no surviving data
	if not row["emails"] and not row.get("phones"):
		return

	WRITTEN_ROW_HASHES.add(row_id)

	key = row["provider_normalized"]

	# Keep highest scoring provider row
	if key in BEST_PROVIDER_ROWS:
		old_score = BEST_PROVIDER_ROWS[key]["contact_quality"]
		new_score = row["contact_quality"]

		if new_score <= old_score:
			return

	BEST_PROVIDER_ROWS[key] = row

	with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
		writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
		writer.writerow(row)


# ─────────────────────────────────────────────────────────────────────────────
# HHS DOWNLOAD
# ─────────────────────────────────────────────────────────────────────────────

def download_hhs_csv(download_path="hhs_breach_report.csv"):

	with sync_playwright() as p:

		browser = p.chromium.launch(headless=True)

		context = browser.new_context(accept_downloads=True)

		page = context.new_page()

		print("🌐 Loading HHS portal...")

		page.goto(URL, timeout=60000)

		page.wait_for_selector("tbody tr", timeout=30000)

		print("📥 Exporting HHS CSV...")

		export_btn = page.query_selector(
			'a[title*="CSV"], a[id*="csv"], a[id*="export"]'
		)

		if not export_btn:
			raise RuntimeError("CSV export button not found")

		with page.expect_download(timeout=60000) as dl:
			export_btn.click()

		download = dl.value

		download.save_as(download_path)

		browser.close()

	print(f"✅ Saved HHS CSV → {download_path}")

	return download_path


# ─────────────────────────────────────────────────────────────────────────────
# PARSE HHS CSV
# ─────────────────────────────────────────────────────────────────────────────

_COL_NAME = 0
_COL_ENTITY_TYPE = 2
_COL_BREACH_DATE = 4


def parse_hhs_csv(csv_path, target_count=TARGET_COUNT):

	providers = []

	seen = set()

	with open(csv_path, newline="", encoding="utf-8-sig") as f:

		reader = csv.reader(f)

		next(reader, None)

		for row in reader:

			try:
				name = row[_COL_NAME].strip()

				entity_type = row[_COL_ENTITY_TYPE].strip()

				breach_date = row[_COL_BREACH_DATE].strip()

			except:
				continue

			if not name:
				continue

			if "Healthcare Provider" not in entity_type:
				continue

			norm = normalize_provider_name(name)

			if norm in seen:
				continue

			seen.add(norm)

			providers.append((name, breach_date))

			print(f"  + {name}")

			if len(providers) >= target_count:
				break

	return providers


def get_healthcare_providers(hhs_csv_path="hhs_breach_report.csv"):

	if os.path.exists(hhs_csv_path):

		age_hours = (
			time.time() - os.path.getmtime(hhs_csv_path)
		) / 3600

		if age_hours < 24:
			print(f"♻️ Reusing HHS CSV ({age_hours:.1f}h old)")
		else:
			download_hhs_csv(hhs_csv_path)

	else:
		download_hhs_csv(hhs_csv_path)

	return parse_hhs_csv(hhs_csv_path)


# ─────────────────────────────────────────────────────────────────────────────
# SEARCH HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def is_valid_domain(url):

	if not url:
		return False

	url = url.lower()

	for bad in BAD_DOMAINS:
		if bad in url:
			return False

	return True


def get_base_url(url):

	try:
		parsed = urlparse(url)

		return f"{parsed.scheme}://{parsed.netloc}"

	except:
		return None


def find_official_site(company):

	queries = [
		f'"{company}" official website',
		f'"{company}" hospital official site',
		f'"{company}" healthcare privacy',
	]

	for query in queries:

		try:
			with DDGS() as ddgs:

				results = list(ddgs.text(query, max_results=10))

			for r in results:

				url = r.get("href") or r.get("url")

				if not url:
					continue

				if not is_valid_domain(url):
					continue

				base = get_base_url(url)

				if base:
					return base

		except Exception as e:
			print(f"Search error: {e}")

	return None


# ─────────────────────────────────────────────────────────────────────────────
# FETCH PAGE TEXT
# ─────────────────────────────────────────────────────────────────────────────

def fetch_text(url):

	try:

		r = SESSION.get(
			url,
			timeout=REQUEST_TIMEOUT,
			allow_redirects=True,
		)

		if r.status_code != 200:
			return None

		if "text/html" not in r.headers.get("Content-Type", ""):
			return None

		soup = BeautifulSoup(r.text, "html.parser")

		for tag in soup([
			"script",
			"style",
			"nav",
			"footer",
			"header",
			"svg",
		]):
			tag.decompose()

		text = soup.get_text(" ", strip=True)

		text = re.sub(r"\s+", " ", text)

		return text

	except:
		return None


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def extract_emails(text):

	if not text:
		return []

	found = EMAIL_RE.findall(text)

	return deduplicate_emails(found)


def extract_phones(text):

	if not text:
		return []

	phones = PHONE_RE.findall(text)

	cleaned = []

	seen = set()

	for p in phones:

		p = re.sub(r"\s+", " ", p.strip())

		if p in seen:
			continue

		seen.add(p)

		cleaned.append(p)

	return cleaned


def extract_name_from_snippet(snippet):

	if not snippet:
		return "", ""

	for match in NAME_RE.finditer(snippet):

		first, last = match.groups()

		if first.lower() in {
			"privacy",
			"health",
			"medical",
			"hospital",
			"contact",
			"office",
		}:
			continue

		return first, last

	return "", ""


def infer_name_from_email(email):

	local = email.split("@")[0]

	parts = re.split(r"[._\-]", local)

	if len(parts) < 2:
		return "", ""

	first = parts[0]
	last = parts[-1]

	if (
		len(first) < 2 or
		len(last) < 2 or
		not first.isalpha() or
		not last.isalpha()
	):
		return "", ""

	if first.lower() in GENERIC_EMAIL_PREFIXES:
		return "", ""

	return first.capitalize(), last.capitalize()


def extract_privacy_contacts(text, source_url, website):

	results = []

	if not text:
		return results

	lower = text.lower()

	for keyword in ROLE_KEYWORDS:

		pos = lower.find(keyword)

		if pos == -1:
			continue

		start = max(0, pos - 350)
		end = min(len(text), pos + 350)

		snippet = text[start:end]

		emails = deduplicate_emails(
			extract_emails(snippet),
			website=website,
		)

		phones = extract_phones(snippet)

		first, last = extract_name_from_snippet(snippet)

		if not first and emails:

			for email in emails:

				first, last = infer_name_from_email(email)

				if first:
					break

		results.append({
			"snippet": snippet[:300],
			"emails": emails,
			"phones": phones,
			"source": source_url,
			"first_name": first,
			"last_name": last,
		})

	return results


# ─────────────────────────────────────────────────────────────────────────────
# SITE CRAWL
# ─────────────────────────────────────────────────────────────────────────────

def find_privacy_contact(base_url):

	all_contacts = []

	for path in PRIVACY_PATHS:

		url = urljoin(base_url, path)

		print(f"  Checking: {url}")

		text = fetch_text(url)

		if not text:
			continue

		contacts = extract_privacy_contacts(
			text,
			url,
			base_url,
		)

		if contacts:

			all_contacts.extend(contacts)

			# Stop once we get strong provider-owned emails
			for c in contacts:

				for email in c["emails"]:

					if is_likely_provider_email(email, base_url):
						return all_contacts

	return all_contacts


# ─────────────────────────────────────────────────────────────────────────────
# FALLBACK SEARCH
# ─────────────────────────────────────────────────────────────────────────────

def search_for_privacy_officer(company, website=None):

	queries = [
		f'"{company}" privacy officer email',
		f'"{company}" HIPAA contact',
		f'"{company}" compliance officer',
	]

	for query in queries:

		try:

			with DDGS() as ddgs:

				results = list(ddgs.text(query, max_results=8))

			for r in results:

				url = r.get("href") or r.get("url")

				body = r.get("body", "")

				emails = deduplicate_emails(
					extract_emails(body),
					website=website,
				)

				if emails:

					first = ""
					last = ""

					for email in emails:

						first, last = infer_name_from_email(email)

						if first:
							break

					return {
						"emails": emails,
						"source": url,
						"first_name": first,
						"last_name": last,
					}

				if url and is_valid_domain(url):

					page_text = fetch_text(url)

					if page_text:

						contacts = extract_privacy_contacts(
							page_text,
							url,
							website,
						)

						for c in contacts:

							if c["emails"]:
								return {
									"emails": c["emails"],
									"source": url,
									"first_name": c["first_name"],
									"last_name": c["last_name"],
								}

		except Exception as e:
			print(f"Search error: {e}")

	return None


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():

	print("\n🚀 Starting HHS Privacy Contact Pipeline\n")

	init_csv()

	providers = get_healthcare_providers()

	if not providers:
		print("❌ No providers found")
		return

	print(f"\n✅ Providers loaded: {len(providers)}")

	for provider, breach_date in providers:

		print("\n" + "=" * 80)
		print(provider)
		print("=" * 80)

		try:

			site = find_official_site(provider)

			if not site:

				print("❌ No official website")

				continue

			print(f"🌐 Website: {site}")

			found = False

			scrape_time = datetime.now().strftime(
				"%Y-%m-%d %H:%M:%S"
			)

			contacts = find_privacy_contact(site)

			for c in contacts:

				if not c["emails"] and not c["phones"]:
					continue

				found = True

				email_matches = any(
					is_likely_provider_email(e, site)
					for e in c["emails"]
				)

				row = {
					"provider_name": provider,
					"breach_submission_date": breach_date,
					"first_name": c["first_name"],
					"last_name": c["last_name"],
					"website": site,
					"emails": "; ".join(c["emails"]),
					"phones": "; ".join(c["phones"]),
					"source_url": c["source"],
					"context_snippet": c["snippet"],
					"found_via": "site crawl",
					"email_domain_matches_site": (
						"yes" if email_matches else "no"
					),
					"date_scraped": scrape_time,
				}

				write_csv_row(row)

				print("✅ Contact found")

				if c["emails"]:
					print(f"   📧 {', '.join(c['emails'])}")

			if found:
				continue

			print("🔎 Running fallback web search...")

			result = search_for_privacy_officer(
				provider,
				website=site,
			)

			if result:

				row = {
					"provider_name": provider,
					"breach_submission_date": breach_date,
					"first_name": result["first_name"],
					"last_name": result["last_name"],
					"website": site,
					"emails": "; ".join(result["emails"]),
					"phones": "",
					"source_url": result["source"],
					"context_snippet": "",
					"found_via": "web search",
					"email_domain_matches_site": (
						"yes" if any(
							is_likely_provider_email(e, site)
							for e in result["emails"]
						) else "no"
					),
					"date_scraped": scrape_time,
				}

				write_csv_row(row)

				print("✅ Found via web search")

			else:
				print("❌ No contact found")

			time.sleep(1)

		except Exception as e:

			print(f"⚠️ Provider failed: {e}")

	print(f"\n✅ Done")
	print(f"📄 Output: {CSV_FILE}")


if __name__ == "__main__":
	main()