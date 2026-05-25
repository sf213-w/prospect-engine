import csv
import re
import requests

from urllib.parse import urlparse
from bs4 import BeautifulSoup
from ddgs import DDGS


INPUT_CSV = "filtered_hhs_breaches.csv"

OUTPUT_CSV = "org_intelligence.csv"


BAD_DOMAINS = {
	"linkedin.com",
	"facebook.com",
	"wikipedia.org",
	"healthgrades.com",
	"yelp.com",
	"hhs.gov",
}


TECH_STACK_KEYWORDS = {
	"epic": "Epic",
	"cerner": "Cerner",
	"athenahealth": "Athenahealth",
	"nextgen": "NextGen",
	"meditech": "Meditech",
	"okta": "Okta",
}


SECURITY_KEYWORDS = [
	"ransomware",
	"phishing",
	"hipaa",
	"privacy",
	"cybersecurity",
]


HEADERS = {
	"User-Agent": "Mozilla/5.0"
}


# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def get_root_domain(url):

	try:
		netloc = urlparse(url).netloc.lower()

		netloc = netloc.replace("www.", "")

		return netloc

	except:
		return ""


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


# -------------------------------------------------------------------
# WEBSITE SEARCH
# -------------------------------------------------------------------

def find_official_site(company):

	queries = [
		f'"{company}" official website',
		f'"{company}" healthcare',
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

		except:
			pass

	return ""


# -------------------------------------------------------------------
# FETCH TEXT
# -------------------------------------------------------------------

def fetch_text(url):

	try:

		r = requests.get(
			url,
			timeout=15,
			headers=HEADERS,
		)

		if r.status_code != 200:
			return ""

		soup = BeautifulSoup(r.text, "html.parser")

		text = soup.get_text(" ", strip=True)

		text = re.sub(r"\s+", " ", text)

		return text.lower()

	except:
		return ""


# -------------------------------------------------------------------
# DETECTORS
# -------------------------------------------------------------------

def detect_technologies(text):

	found = []

	for keyword, label in TECH_STACK_KEYWORDS.items():

		if keyword in text:
			found.append(label)

	return "; ".join(sorted(set(found)))


def detect_security_keywords(text):

	found = []

	for keyword in SECURITY_KEYWORDS:

		if keyword in text:
			found.append(keyword)

	return "; ".join(sorted(set(found)))


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

with open(INPUT_CSV, newline="", encoding="utf-8") as infile, \
	 open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as outfile:

	reader = csv.DictReader(infile)

	fieldnames = reader.fieldnames + [
		"website",
		"root_domain",
		"apollo_company_hint",
		"linkedin_company_hint",
		"technology_indicators",
		"security_keywords",
	]

	writer = csv.DictWriter(outfile, fieldnames=fieldnames)

	writer.writeheader()

	for row in reader:

		org = row["organization_name"]

		print(f"\n{org}")

		site = find_official_site(org)

		root = get_root_domain(site)

		text = fetch_text(site)

		row["website"] = site

		row["root_domain"] = root

		row["apollo_company_hint"] = root

		row["linkedin_company_hint"] = f"{org} {root}"

		row["technology_indicators"] = detect_technologies(text)

		row["security_keywords"] = detect_security_keywords(text)

		writer.writerow(row)

		print(site)

print(f"\nDone -> {OUTPUT_CSV}")