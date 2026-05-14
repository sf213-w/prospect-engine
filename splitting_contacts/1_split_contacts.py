import sys
import os
import re
import pandas as pd
from urllib.parse import urlparse

DEFAULT_INPUT = "../pipeline/raw_data.csv"
DEFAULT_OUTPUT = "1_output/"

EMAIL_PRIORITY = [
	"Person - Email - Work",
	"Person - Email - Home",
	"Person - Email - Other",
]

HEADER_MAP = {
	"Person - First name": "first_name",
	"Person - Last name": "last_name",
	"Person - Title": "title",
	"Person - Phone - Work": "phone",
	"Person - CompanyName": "company_name",
	"Person - Organization": "organization",
	"Person - City": "city",
	"Person - State": "state",
	"Person - Website": "website",
	"Person - Role": "role",
	"Person - Marketing status": "marketing_status",
	"Person - LinkedInCompany": "linkedin_company",
}

PERSONAL_DOMAINS = {
	"gmail.com", "googlemail.com", "yahoo.com", "hotmail.com",
	"outlook.com", "live.com", "icloud.com", "me.com",
	"aol.com", "protonmail.com",
}

GENERIC_PREFIXES = {
	"info", "hello", "support", "admin", "office",
	"contact", "sales", "billing", "team",
}

COMMON_SECOND_LEVEL_TLDS = {"co.uk", "org.uk", "com.au"}

# --------------------------------------------------------------
# SPAM DETECTION
# --------------------------------------------------------------

SPAM_URL_PATTERNS = [
	r"https?://\S+",
	r"bit\.ly",
	r"t\.co",
	r"page\.link",
	r"goo\.gl",
]

SPAM_KEYWORDS = [
	"want to be my bf",
	"sup!",
	"click here",
	"make money",
	"free money",
	"urgent",
	"crypto",
	"investment opportunity",
	"dear",
]

# --------------------------------------------------------------
# EMAIL HANDLING (STRICT)
# --------------------------------------------------------------

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

def extract_primary_email(value):
	"""
	Extract ONLY the first valid email from a noisy field.
	Guarantees NeverBounce-safe single email output.
	"""
	if not value:
		return ""

	emails = EMAIL_REGEX.findall(str(value).lower())

	if not emails:
		return ""

	return emails[0].strip()


def is_valid_email(email):
	"""Strict validation for final output"""
	return bool(email and EMAIL_REGEX.fullmatch(email))


def safe_str(v):
	if pd.isna(v):
		return ""
	return str(v).strip()


def get_primary_email(row):
	"""
	Priority-based email selection:
	Work > Home > Other
	"""
	for col in EMAIL_PRIORITY:
		value = safe_str(row.get(col))
		email = extract_primary_email(value)

		if email:
			return email

	return ""


# --------------------------------------------------------------
# DOMAIN HELPERS
# --------------------------------------------------------------

def extract_domain(email):
	if "@" not in email:
		return ""
	return email.split("@", 1)[1].lower()


def extract_root_domain(domain):
	if not domain:
		return ""

	parts = domain.split(".")
	if len(parts) < 2:
		return domain

	joined = ".".join(parts[-2:])
	if joined in COMMON_SECOND_LEVEL_TLDS and len(parts) >= 3:
		return ".".join(parts[-3:])

	return joined


# --------------------------------------------------------------
# BUSINESS LOGIC
# --------------------------------------------------------------

def normalize_org(text):
	text = safe_str(text).lower()
	text = re.sub(r"[^a-z0-9\s]", " ", text)

	text = re.sub(
		r"\b(llc|inc|corp|corporation|ltd|pllc|pc|pa|group|company)\b",
		"",
		text,
	)

	text = re.sub(r"\s+", " ", text).strip()
	return text


def infer_provider_signal(text):
	text = safe_str(text).lower()

	provider_words = [
		"dds", "dmd", "orthodontics",
		"family dentistry", "endodontics",
		"periodontics", "prosthodontics",
		"pediatric dental",
	]

	return any(w in text for w in provider_words)


def classify_contact(email, domain):
	if not domain:
		return "invalid"

	if domain.endswith(".edu") or ".edu." in domain:
		return "edu"

	if domain in PERSONAL_DOMAINS:
		return "personal"

	local = email.split("@", 1)[0].lower() if "@" in email else ""

	if local in GENERIC_PREFIXES:
		return "generic_inbox"

	return "company"


# --------------------------------------------------------------
# SPAM FILTERS
# --------------------------------------------------------------

def is_spam_row(row):
	fields = [
		"first_name", "last_name",
		"title", "organization",
		"company_name", "email",
	]

	blob = " ".join(
		safe_str(row.get(f)).lower()
		for f in fields
	)

	if any(re.search(p, blob) for p in SPAM_URL_PATTERNS):
		return True

	if any(k in blob for k in SPAM_KEYWORDS):
		return True

	email = safe_str(row.get("email")).lower()
	if email and any(x in email for x in ["ffrty", "click", "promo", "offer"]):
		return True

	if blob:
		alpha_ratio = sum(c.isalpha() for c in blob) / max(len(blob), 1)
		if alpha_ratio < 0.5:
			return True

	return False


def is_low_quality_contact(row):
	has_identity = any([
		safe_str(row.get("first_name")),
		safe_str(row.get("last_name")),
		safe_str(row.get("organization")),
		safe_str(row.get("company_name")),
	])

	has_email = bool(safe_str(row.get("email")))

	return has_email and not has_identity


# --------------------------------------------------------------
# MAIN
# --------------------------------------------------------------

def main():

	input_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
	output_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT

	os.makedirs(output_dir, exist_ok=True)

	print(f"Loading: {input_file}")

	df = pd.read_csv(input_file, dtype=str, low_memory=False)

	print(f"Loaded {len(df):,} rows")

	# ----------------------------------------------------------
	# Rename headers
	# ----------------------------------------------------------
	df = df.rename(columns=HEADER_MAP)

	# ----------------------------------------------------------
	# DROP SPAM EARLY
	# ----------------------------------------------------------
	before = len(df)

	df = df[
		~df.apply(is_spam_row, axis=1) &
		~df.apply(is_low_quality_contact, axis=1)
	]

	print(f"Removed rows: {before - len(df):,}")

	# ----------------------------------------------------------
	# EMAIL (STRICT SINGLE VALUE ENFORCEMENT)
	# ----------------------------------------------------------
	df["email"] = df.apply(get_primary_email, axis=1)

	# FINAL SAFETY PASS (CRITICAL FOR NEVERBOUNCE)
	df["email"] = df["email"].apply(extract_primary_email)

	# DROP INVALID EMAILS
	before = len(df)
	df = df[df["email"].apply(is_valid_email)]
	print(f"Dropped invalid emails: {before - len(df):,}")

	# ----------------------------------------------------------
	# DOMAIN FIELDS
	# ----------------------------------------------------------
	df["domain"] = df["email"].apply(extract_domain)
	df["root_domain"] = df["domain"].apply(extract_root_domain)

	# ----------------------------------------------------------
	# NORMALIZATION
	# ----------------------------------------------------------
	df["normalized_org"] = (
		df["company_name"]
		.fillna(df["organization"])
		.apply(normalize_org)
	)

	df["likely_provider"] = (
		df["company_name"]
		.fillna(df["organization"])
		.apply(infer_provider_signal)
	)

	# ----------------------------------------------------------
	# CONTACT TYPE
	# ----------------------------------------------------------
	df["contact_type"] = df.apply(
		lambda row: classify_contact(row["email"], row["domain"]),
		axis=1,
	)

	# ----------------------------------------------------------
	# FINAL COLUMNS
	# ----------------------------------------------------------
	final_columns = [
		"first_name", "last_name", "email",
		"title", "phone",
		"company_name", "organization",
		"city", "state", "website",
		"normalized_org",
		"root_domain",
		"likely_provider",
		"contact_type",
	]

	df = df[final_columns]

	# ----------------------------------------------------------
	# SAVE OUTPUTS
	# ----------------------------------------------------------
	for category in ["company", "personal", "edu", "generic_inbox"]:

		subset = df[df["contact_type"] == category]

		outfile = os.path.join(output_dir, f"{category}_contacts.csv")

		subset.to_csv(outfile, index=False)

		print(f"Saved: {outfile} ({len(subset):,} rows)")


if __name__ == "__main__":
	main()