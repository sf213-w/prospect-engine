"""
3_split_by_market.py
====================

Stage 3:
- Removes junk
- Removes low-confidence classifications
- Deduplicates
- Splits into market datasets
"""

import os
import re
import pandas as pd

INPUT_FILE = "2_output/company_contacts_categorized.csv"

OUTPUT_DIR = "3_output"

MIN_CONFIDENCE = 0.50

KEEP_COLUMNS = [
	"first_name",
	"last_name",
	"email",
	"title",
	"phone",

	"company_name",
	"organization",
	"city",
	"state",
	"website",

	"normalized_org",
	"root_domain",

	"category",
	"category_confidence",
	"category_source",

	"contact_quality",
]

MARKET_SEGMENTS = {
	"dental.csv": {
		"Dental",
	},

	"mental_health.csv": {
		"Mental Health / Counseling",
		"Substance Abuse / Addiction Recovery",
	},

	"wellness.csv": {
		"Wellness / Integrative / Alternative",
		"Chiropractic",
		"Physical Therapy / Rehab",
		"Home Health / Hospice",
	},

	"eye_care.csv": {
		"Vision / Optometry",
	},
}

VALID_EMAIL_PATTERN = re.compile(
	r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
	re.IGNORECASE
)

SPAM_DOMAINS = {
	"example.com",
	"mailinator.com",
	"guerrillamail.com",
	"trashmail.com",
	"yopmail.com",
}


def safe_str(value):

	if pd.isna(value):
		return ""

	return str(value).strip()


def is_invalid_email(email):

	email = safe_str(email).lower()

	if not email:
		return True

	if not VALID_EMAIL_PATTERN.match(email):
		return True

	domain = email.split("@")[-1]

	if domain in SPAM_DOMAINS:
		return True

	return False


def is_junk_row(row):

	email = row.get("email")

	if is_invalid_email(email):
		return True

	return False


def deduplicate(df):

	df = df.drop_duplicates()

	df = (
		df
		.sort_values(
			[
				"category_confidence",
				"contact_quality",
			],
			ascending=False
		)
	)

	df = df.drop_duplicates(
		subset=["email"],
		keep="first"
	)

	df = df.drop_duplicates(
		subset=[
			"normalized_org",
			"root_domain",
			"first_name",
			"last_name",
		],
		keep="first"
	)

	return df


def trim_columns(df):

	available = [
		col
		for col in KEEP_COLUMNS
		if col in df.columns
	]

	return df[available]


def save(df, filename):

	path = os.path.join(OUTPUT_DIR, filename)

	df.to_csv(path, index=False)

	print(f"{filename:<30} {len(df):>8,} rows")


def main():

	os.makedirs(OUTPUT_DIR, exist_ok=True)

	df = pd.read_csv(INPUT_FILE, low_memory=False)

	print(f"Loaded {len(df):,} rows")

	df = trim_columns(df)

	junk_mask = df.apply(is_junk_row, axis=1)

	df = df[~junk_mask].copy()

	print(f"Removed {junk_mask.sum():,} junk rows")

	review_mask = (
		(df["category_confidence"] < MIN_CONFIDENCE)
		|
		(df["category"] == "Ambiguous / Needs Review")
	)

	review = df[review_mask].copy()

	save(review, "needs_review.csv")

	df = df[~review_mask].copy()

	before = len(df)

	df = deduplicate(df)

	print(f"Removed {before - len(df):,} duplicates")

	assigned = pd.Series(False, index=df.index)

	for filename, categories in MARKET_SEGMENTS.items():

		mask = df["category"].isin(categories)

		subset = df[mask].copy()

		assigned |= mask

		save(subset, filename)

	other = df[~assigned].copy()

	save(other, "other.csv")

	report = (
		df.groupby("category")
		.agg(
			contacts=("category", "count"),
			companies=("company_name", "nunique"),
			avg_confidence=(
				"category_confidence",
				"mean"
			),
		)
		.reset_index()
		.sort_values(
			"contacts",
			ascending=False
		)
	)

	save(report, "market_report.csv")

	print("\nDone.")


if __name__ == "__main__":
	main()