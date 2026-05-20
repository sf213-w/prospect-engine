# 3_split_by_market.py

import pandas as pd
import os
import re

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

INPUT_FILE = "2_output/company_contacts_categorized.csv"
OUTPUT_DIR = "3_output"

CATEGORY_COLUMN = "category"
CONFIDENCE_COLUMN = "category_confidence"

LOW_CONFIDENCE_THRESHOLD = 0.55

CATEGORY_MAP = {
	"mental_health.csv": [
		"Mental Health / Counseling",
		"Substance Abuse / Addiction Recovery",
	],

	"dental.csv": [
		"Dental",
	],

	"eye_care.csv": [
		"Vision / Optometry",
	],

	"wellness.csv": [
		"Chiropractic",
		"Physical Therapy / Rehab",
		"Wellness / Integrative / Alternative",
	],
}

EXCLUDED_PROVIDER_CATEGORIES = {
	"Healthcare IT / SaaS",
	"Billing / Revenue Cycle",
	"Insurance / Network",
	"Dental Management Group",
	"Dental Manufacturer / Supplier",
	"Medical Education",
	"Consulting / Compliance",
}

SPAM_PATTERNS = [
	r"test",
	r"example\.com",
	r"fake",
	r"spam",
	r"noreply",
	r"no-reply",
	r"mailinator",
	r"asdf",
	r"qwerty",
]

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def safe_str(v):

	if pd.isna(v):
		return ""

	return str(v).strip()


def normalize_confidence(v):

	if pd.isna(v):
		return 0.5

	v = str(v).strip().lower()

	mapping = {
		"high": 0.95,
		"medium": 0.75,
		"low": 0.40,
		"rules": 0.95,
		"llm": 0.70,
	}

	if v in mapping:
		return mapping[v]

	try:
		return float(v)
	except:
		return 0.5


def is_spam_row(row):

	text = " | ".join([
		safe_str(row.get("first_name")),
		safe_str(row.get("last_name")),
		safe_str(row.get("email")),
		safe_str(row.get("company_name")),
		safe_str(row.get("organization")),
	])

	text = text.lower()

	for pattern in SPAM_PATTERNS:
		if re.search(pattern, text, re.IGNORECASE):
			return True

	return False


def deduplicate(df):

	before = len(df)

	df = df.drop_duplicates().copy()

	# Prefer rows with more populated fields
	df["_filled"] = df.notna().sum(axis=1)

	df = (
		df
		.sort_values("_filled", ascending=False)
		.drop_duplicates(subset=["email"], keep="first")
		.drop(columns=["_filled"])
		.copy()
	)

	removed = before - len(df)

	print(f"Removed {removed:,} duplicate rows")

	return df


def save_subset(df, filename):

	path = os.path.join(OUTPUT_DIR, filename)

	df.to_csv(path, index=False)

	print(f"{filename:<28} {len(df):>8,} rows")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():

	os.makedirs(OUTPUT_DIR, exist_ok=True)

	print(f"Loading: {INPUT_FILE}")

	df = pd.read_csv(INPUT_FILE, dtype=str)

	print(f"Loaded {len(df):,} rows")

	# --------------------------------------------------------------
	# Normalize confidence
	# --------------------------------------------------------------

	df[CONFIDENCE_COLUMN] = (
		df[CONFIDENCE_COLUMN]
		.apply(normalize_confidence)
	)

	# --------------------------------------------------------------
	# Remove spam
	# --------------------------------------------------------------

	spam_mask = df.apply(is_spam_row, axis=1)

	spam = df[spam_mask].copy()

	df = df[~spam_mask].copy()

	save_subset(spam, "spam.csv")

	print(f"Removed {len(spam):,} spam rows")

	# --------------------------------------------------------------
	# Deduplicate
	# --------------------------------------------------------------

	df = deduplicate(df)

	# --------------------------------------------------------------
	# Vendor/Admin split
	# --------------------------------------------------------------

	vendors = df[
		df[CATEGORY_COLUMN].isin(EXCLUDED_PROVIDER_CATEGORIES)
	].copy()

	save_subset(vendors, "vendors_admins.csv")

	# Remove vendors/admins from provider targeting
	df = df[
		~df[CATEGORY_COLUMN].isin(EXCLUDED_PROVIDER_CATEGORIES)
	].copy()

	# --------------------------------------------------------------
	# Needs review bucket
	# --------------------------------------------------------------

	review = df[
		(df[CATEGORY_COLUMN] == "Ambiguous / Needs Review") |
		(df[CONFIDENCE_COLUMN] < LOW_CONFIDENCE_THRESHOLD)
	].copy()

	save_subset(review, "needs_review.csv")

	# Remove review rows from targeting
	df = df.drop(review.index)

	# --------------------------------------------------------------
	# Market segmentation
	# --------------------------------------------------------------

	used_categories = set()

	for filename, categories in CATEGORY_MAP.items():

		used_categories.update(categories)

		subset = df[
			df[CATEGORY_COLUMN].isin(categories)
		].copy()

		save_subset(subset, filename)

	# --------------------------------------------------------------
	# Other bucket
	# --------------------------------------------------------------

	other = df[
		~df[CATEGORY_COLUMN].isin(used_categories)
	].copy()

	save_subset(other, "other.csv")

	# --------------------------------------------------------------
	# Summary
	# --------------------------------------------------------------

	print()
	print("Category Breakdown")
	print("-" * 60)

	counts = (
		df[CATEGORY_COLUMN]
		.value_counts()
		.sort_values(ascending=False)
	)

	for category, count in counts.items():
		print(f"{category:<40} {count:>8,}")

	print("-" * 60)

	print(f"Final Targetable Rows: {len(df):,}")

	print()
	print(f"Done -> {os.path.abspath(OUTPUT_DIR)}")


if __name__ == "__main__":
	main()