# 2_categorize_companies.py

import pandas as pd
import re
import sys
import os

DEFAULT_INPUT = "1_output/company_contacts.csv"
DEFAULT_OUTPUT = "2_output/company_contacts_categorized.csv"

VALID_CATEGORIES = {
	"Dental",
	"Mental Health / Counseling",
	"Family Medicine / Primary Care",
	"Pediatrics",
	"Vision / Optometry",
	"Chiropractic",
	"Physical Therapy / Rehab",
	"Hospital / Health System",
	"Urgent Care",
	"Healthcare IT / SaaS",
	"Billing / Revenue Cycle",
	"Consulting / Compliance",
	"Insurance / Network",
	"Dental Management Group",
	"Dental Manufacturer / Supplier",
	"Medical Education",
	"Other Healthcare",
	"Non-Healthcare",
	"Ambiguous / Needs Review",
}

NON_PROVIDER_RULES = [
	{
		"category": "Billing / Revenue Cycle",
		"patterns": [
			r"billing",
			r"revenue cycle",
			r"claims",
		],
	},

	{
		"category": "Insurance / Network",
		"patterns": [
			r"insurance",
			r"network",
			r"dental plans",
		],
	},

	{
		"category": "Dental Management Group",
		"patterns": [
			r"management",
			r"partners",
			r"dso",
			r"group",
		],
	},

	{
		"category": "Dental Manufacturer / Supplier",
		"patterns": [
			r"technologies",
			r"supplier",
			r"manufacturer",
		],
	},

	{
		"category": "Medical Education",
		"patterns": [
			r"education",
			r"academy",
			r"training",
		],
	},
]

PROVIDER_RULES = [
	{
		"category": "Dental",
		"patterns": [
			r"dental",
			r"dentistry",
			r"orthodont",
			r"endodont",
			r"periodont",
			r"prosthodont",
		],
	},

	{
		"category": "Mental Health / Counseling",
		"patterns": [
			r"mental health",
			r"therapy",
			r"counseling",
		],
	},

	{
		"category": "Vision / Optometry",
		"patterns": [
			r"optometry",
			r"vision",
			r"eye care",
		],
	},
]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def safe_str(v):
	if pd.isna(v):
		return ""
	return str(v).strip()



def build_context(row):

	fields = [
		row.get("company_name"),
		row.get("organization"),
		row.get("website"),
		row.get("title"),
		row.get("root_domain"),
	]

	return " | ".join(
		safe_str(f)
		for f in fields
		if safe_str(f)
	)



def classify_non_provider(text):

	text = text.lower()

	for rule in NON_PROVIDER_RULES:

		for pattern in rule["patterns"]:

			if re.search(pattern, text, re.IGNORECASE):
				return rule["category"], 0.99, "rules"

	return None, 0.0, None



def classify_provider(text):

	text = text.lower()

	for rule in PROVIDER_RULES:

		for pattern in rule["patterns"]:

			if re.search(pattern, text, re.IGNORECASE):
				return rule["category"], 0.98, "rules"

	return "Ambiguous / Needs Review", 0.50, "fallback"


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():

	input_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT

	output_file = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT

	df = pd.read_csv(input_file, dtype=str)

	categories = []
	confidences = []
	sources = []

	for _, row in df.iterrows():

		context = build_context(row)

		category, confidence, source = classify_non_provider(context)

		if not category:
			category, confidence, source = classify_provider(context)

		categories.append(category)
		confidences.append(confidence)
		sources.append(source)

	df["category"] = categories
	df["category_confidence"] = confidences
	df["category_source"] = sources

	# --------------------------------------------------------------
	# Contact quality
	# --------------------------------------------------------------

	def quality(row):

		if row["email"] and row["company_name"]:
			return "high"

		if row["email"]:
			return "medium"

		return "low"

	df["contact_quality"] = df.apply(quality, axis=1)

	df.to_csv(output_file, index=False)

	print(f"Saved: {output_file}")

	print()
	print(df["category"].value_counts())


if __name__ == "__main__":
	main()