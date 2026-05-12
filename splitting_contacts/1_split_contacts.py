"""
1_split_contacts.py
====================

Outputs:
  - edu_contacts.csv
  - personal_contacts.csv
  - company_contacts.csv
  - student_contacts.csv
  - generic_inbox_contacts.csv
  - suspicious_contacts.csv
"""

import sys
import os
import re
import pandas as pd
# find input at pipeline/raw_data.csv
DEFAULT_INPUT = "raw_data.csv"

EMAIL_COLUMNS = [
	"Person - Email - Work",
	"Person - Email - Home",
	"Person - Email - Other",
]

PERSONAL_DOMAINS = {
	"gmail.com", "googlemail.com",
	"yahoo.com", "hotmail.com",
	"outlook.com", "live.com",
	"icloud.com", "me.com",
	"aol.com", "protonmail.com",
	"gmx.com", "comcast.net",
	"att.net",
}

STUDENT_KEYWORDS = {
	"student",
	"students",
	"k12",
	"school",
	"district",
	"isd",
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
}

SUSPICIOUS_PATTERNS = [
	r"^[a-z]+[0-9]{2,}$",
	r"^[0-9]+$",
	r"cool",
	r"dragon",
	r"mike",
]


def get_primary_email(row):
	for col in EMAIL_COLUMNS:
		val = row.get(col, "")
		if pd.notna(val) and str(val).strip():
			return str(val).strip().lower()
	return None


def classify_email(email):

	if not isinstance(email, str) or not email:
		return "no_email"

	if "@" not in email:
		return "invalid"

	local, domain = email.split("@", 1)

	# EDU
	if domain.endswith(".edu") or ".edu." in domain:
		return "edu"

	# Student systems
	for keyword in STUDENT_KEYWORDS:
		if keyword in domain:
			return "student"

	# Personal providers
	if domain in PERSONAL_DOMAINS:
		return "personal"

	# Generic inboxes
	if local in GENERIC_PREFIXES:
		return "generic_inbox"

	# Suspicious aliases
	for pattern in SUSPICIOUS_PATTERNS:
		if re.search(pattern, local):
			return "suspicious"

	return "company"


def save(df, path):
	df.to_csv(path, index=False)
	print(f"Saved: {path:<40} {len(df):>7,} rows")


def main():

	input_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT

	output_dir = (
		sys.argv[2]
		if len(sys.argv) > 2
		else os.path.dirname(input_file) or "."
	)

	os.makedirs(output_dir, exist_ok=True)

	print(f"Loading: {input_file}")

	df = pd.read_csv(input_file, low_memory=False)

	print(f"Loaded {len(df):,} rows")

	df["_primary_email"] = df.apply(get_primary_email, axis=1)
	df["_email_type"] = df["_primary_email"].apply(classify_email)

	categories = {
		"edu": "edu_contacts.csv",
		"student": "student_contacts.csv",
		"personal": "personal_contacts.csv",
		"generic_inbox": "generic_inbox_contacts.csv",
		"suspicious": "suspicious_contacts.csv",
		"company": "company_contacts.csv",
	}

	for category, filename in categories.items():

		outfile = os.path.join(output_dir, filename)

		subset = (
			df[df["_email_type"] == category]
			.drop(columns=["_primary_email", "_email_type"])
		)

		save(subset, outfile)

	no_email = len(df[df["_email_type"] == "no_email"])

	print(f"\nNo email rows: {no_email:,}")


if __name__ == "__main__":
	main()