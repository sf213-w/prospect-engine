"""
1_split_contacts.py
===================

Stage 1:
- Simplifies headers
- Chooses a single canonical email
- Extracts domains
- Normalizes organizations
- Scores contact quality
- Adds healthcare hints
- Deduplicates contacts
- Splits into datasets

Outputs:
  - company_contacts.csv
  - personal_contacts.csv
  - edu_contacts.csv
  - student_contacts.csv
  - invalid_contacts.csv
"""

import sys
import os
import re
import pandas as pd

DEFAULT_INPUT = "../pipeline/raw_data.csv"
DEFAULT_OUTPUT = "1_output"

EMAIL_PRIORITY = [
	"Person - Email - Work",
	"Person - Email - Home",
	"Person - Email - Other",
]

COLUMN_MAP = {
	"Person - Marketing status": "marketing_status",
	"Person - Double opt-in": "double_opt_in",
	"Person - First name": "first_name",
	"Person - Last name": "last_name",
	"Person - ReferralURL": "referral_url",
	"Person - Phone - Work": "phone",
	"Person - Website": "website",
	"Person - Title": "title",
	"Person - State": "state",
	"Person - Role": "role",
	"Person - Organization": "organization",
	"Person - LinkedInCompany": "linkedin_company",
	"Person - Employees": "employees",
	"Person - CompanyName": "company_name",
	"Person - City": "city",
	"Person - Name": "full_name",
	"Person - Sweet Spot": "sweet_spot",
	"Person - Sales Process Stage": "sales_process_stage",
	"Person - Sample Modules": "sample_modules",
	"Person - Person created": "date_created",
}

PERSONAL_DOMAINS = {
	"gmail.com",
	"googlemail.com",
	"yahoo.com",
	"hotmail.com",
	"outlook.com",
	"live.com",
	"icloud.com",
	"me.com",
	"aol.com",
	"protonmail.com",
	"gmx.com",
	"comcast.net",
	"att.net",
}

GENERIC_PREFIXES = {
	"info",
	"support",
	"admin",
	"contact",
	"hello",
	"office",
	"sales",
	"billing",
	"team",
	"marketing",
	"privacy",
	"compliance",
	"careers",
	"hr",
	"help",
}

STUDENT_KEYWORDS = {
	"student",
	"students",
	"school",
	"district",
	"isd",
	"k12",
}

HEALTHCARE_KEYWORDS = {
	"dental": "Dental",
	"dentistry": "Dental",
	"orthodont": "Dental",
	"endodont": "Dental",

	"behavioralhealth": "Mental Health / Counseling",
	"mentalhealth": "Mental Health / Counseling",
	"therapy": "Mental Health / Counseling",
	"counsel": "Mental Health / Counseling",

	"vision": "Vision / Optometry",
	"optometry": "Vision / Optometry",
	"eye": "Vision / Optometry",

	"hospital": "Hospital / Health System",
	"healthsystem": "Hospital / Health System",

	"chiropractic": "Chiropractic",

	"rehab": "Physical Therapy / Rehab",
	"physicaltherapy": "Physical Therapy / Rehab",
}

VALID_EMAIL_PATTERN = re.compile(
	r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
	re.IGNORECASE
)


def safe_str(value):

	if pd.isna(value):
		return ""

	return str(value).strip()


def choose_email(row):

	for col in EMAIL_PRIORITY:

		email = safe_str(row.get(col)).lower()

		if email:
			return email

	return ""


def extract_domain(email):

	if "@" not in email:
		return ""

	return email.split("@", 1)[1].lower().strip()


def root_domain(domain):

	if not domain:
		return ""

	parts = domain.split(".")

	if len(parts) >= 2:
		return ".".join(parts[-2:])

	return domain


def normalize_org(org):

	org = safe_str(org).lower()

	replacements = {
		"&": "and",
		"st.": "saint",
		"hosp": "hospital",
		"ctr": "center",
	}

	for k, v in replacements.items():
		org = org.replace(k, v)

	org = re.sub(r"[^a-z0-9 ]", " ", org)
	org = re.sub(r"\s+", " ", org)

	return org.strip()


def infer_domain_category(domain):

	if not domain:
		return ""

	domain = domain.replace("-", "").replace(".", "")

	for keyword, category in HEALTHCARE_KEYWORDS.items():

		if keyword in domain:
			return category

	return ""


def classify_contact(email, domain):

	if not email:
		return "invalid"

	if not VALID_EMAIL_PATTERN.match(email):
		return "invalid"

	if not domain:
		return "invalid"

	if domain in PERSONAL_DOMAINS:
		return "personal"

	if domain.endswith(".edu") or ".edu." in domain:
		return "edu"

	for kw in STUDENT_KEYWORDS:
		if kw in domain:
			return "student"

	return "company"


def detect_generic_inbox(email):

	if "@" not in email:
		return False

	local = email.split("@", 1)[0].lower().strip()

	return local in GENERIC_PREFIXES


def score_contact(email, generic):

	if not email:
		return "low"

	if generic:
		return "medium"

	return "high"


def save(df, path):

	df.to_csv(path, index=False)

	print(f"Saved: {path:<40} {len(df):>8,} rows")


def main():

	input_file = (
		sys.argv[1]
		if len(sys.argv) > 1
		else DEFAULT_INPUT
	)

	output_dir = (
		sys.argv[2]
		if len(sys.argv) > 2
		else DEFAULT_OUTPUT
	)

	os.makedirs(output_dir, exist_ok=True)

	print(f"Loading: {input_file}")

	df = pd.read_csv(input_file, low_memory=False)

	print(f"Loaded {len(df):,} rows")

	df = df.rename(columns=COLUMN_MAP)

	df["email"] = df.apply(choose_email, axis=1)

	df["domain"] = df["email"].apply(extract_domain)

	df["root_domain"] = df["domain"].apply(root_domain)

	df["normalized_org"] = (
		df["company_name"]
		.apply(normalize_org)
	)

	df["domain_category_hint"] = (
		df["root_domain"]
		.apply(infer_domain_category)
	)

	df["is_generic_inbox"] = (
		df["email"]
		.apply(detect_generic_inbox)
	)

	df["contact_quality"] = df.apply(
		lambda row: score_contact(
			row["email"],
			row["is_generic_inbox"]
		),
		axis=1
	)

	df["contact_type"] = df.apply(
		lambda row: classify_contact(
			row["email"],
			row["root_domain"]
		),
		axis=1
	)

	df = df.drop_duplicates(
		subset=["email"],
		keep="first"
	)

	categories = {
		"company": "company_contacts.csv",
		"personal": "personal_contacts.csv",
		"edu": "edu_contacts.csv",
		"student": "student_contacts.csv",
		"invalid": "invalid_contacts.csv",
	}

	for category, filename in categories.items():

		subset = df[df["contact_type"] == category]

		save(
			subset,
			os.path.join(output_dir, filename)
		)

	print("\nDone.")


if __name__ == "__main__":
	main()