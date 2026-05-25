import csv
import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


INPUT_CSV = "org_intelligence.csv"
OUTPUT_CSV = "apollo_ready_contacts.csv"


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

PHONE_RE = re.compile(
	r"(?:\+?1[\s\-.]?)?"
	r"(?:\(?\d{3}\)?[\s\-.]?)"
	r"\d{3}[\s\-.]?\d{4}"
)

TITLE_RE = re.compile(
	r"(privacy officer|compliance officer|chief information officer|cio|ciso|director of compliance)",
	re.I
)


PRIVACY_PATHS = [
	"/privacy",
	"/privacy-policy",
	"/hipaa",
	"/contact",
	"/contact-us",
	"/leadership",
	"/team",
	"/executives",
]


HEADERS = {"User-Agent": "Mozilla/5.0"}


# ------------------------------------------------------------
# FETCH
# ------------------------------------------------------------

def fetch_text(url):
	try:
		r = requests.get(url, timeout=15, headers=HEADERS)
		if r.status_code != 200:
			return ""

		soup = BeautifulSoup(r.text, "html.parser")

		for tag in soup(["script", "style", "nav", "footer"]):
			tag.decompose()

		text = soup.get_text(" ", strip=True)
		return re.sub(r"\s+", " ", text)

	except:
		return ""


# ------------------------------------------------------------
# EXTRACTORS
# ------------------------------------------------------------

def extract_emails(text):
	return set(EMAIL_RE.findall(text.lower()))


def extract_phones(text):
	return set(PHONE_RE.findall(text))


def extract_titles(text):
	return set(TITLE_RE.findall(text))


def infer_name_from_email(email):
	local = email.split("@")[0]
	parts = re.split(r"[._\-]", local)

	if len(parts) < 2:
		return "", ""

	first, last = parts[0], parts[-1]

	if not first.isalpha() or not last.isalpha():
		return "", ""

	return first.capitalize(), last.capitalize()


# ------------------------------------------------------------
# DOMAIN NORMALIZATION (KEY FIX)
# ------------------------------------------------------------

def get_root_domain(url):
	try:
		return urlparse(url).netloc.lower().replace("www.", "")
	except:
		return ""


def is_valid_state(state):
	return bool(re.fullmatch(r"[A-Z]{2}", str(state).strip()))


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

seen_orgs = set()

with open(INPUT_CSV, newline="", encoding="utf-8") as infile, \
	 open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as outfile:

	reader = csv.DictReader(infile)

	fieldnames = reader.fieldnames + [
		"contact_emails",
		"contact_first_names",
		"contact_last_names",
		"contact_phones",
		"contact_titles",
		"source_urls",
	]

	writer = csv.DictWriter(outfile, fieldnames=fieldnames)
	writer.writeheader()

	for row in reader:

		org = row["organization_name"]
		base = row.get("website", "")
		state = row.get("state", "")

		# --------------------------------------------------------
		# FIX 1: skip bad state rows (your corruption issue)
		# --------------------------------------------------------
		if not is_valid_state(state):
			print(f"Skipping bad state row: {org} -> {state}")
			continue

		if not base:
			continue

		domain = get_root_domain(base)

		# --------------------------------------------------------
		# FIX 2: TRUE ORG DEDUP
		# --------------------------------------------------------
		if domain in seen_orgs:
			continue

		seen_orgs.add(domain)

		print(f"\n{org}")

		all_emails = set()
		all_phones = set()
		all_titles = set()
		all_sources = []

		for path in PRIVACY_PATHS:

			url = urljoin(base, path)

			text = fetch_text(url)

			if len(text) < 200:
				continue

			all_emails |= extract_emails(text)
			all_phones |= extract_phones(text)
			all_titles |= extract_titles(text)
			all_sources.append(url)

		# --------------------------------------------------------
		# OUTPUT 1 ROW PER ORG (FIXED DUPLICATION)
		# --------------------------------------------------------

		first_names = []
		last_names = []

		for email in all_emails:
			f, l = infer_name_from_email(email)
			first_names.append(f)
			last_names.append(l)

		out = dict(row)

		out["contact_emails"] = "; ".join(sorted(all_emails))
		out["contact_first_names"] = "; ".join(sorted(set(first_names)))
		out["contact_last_names"] = "; ".join(sorted(set(last_names)))
		out["contact_phones"] = "; ".join(sorted(all_phones))
		out["contact_titles"] = "; ".join(sorted(all_titles))
		out["source_urls"] = "; ".join(all_sources)

		writer.writerow(out)

		print(f"Emails: {len(all_emails)}")

print(f"\nDone -> {OUTPUT_CSV}")