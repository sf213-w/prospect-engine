"""
2_categorize_companies.py
=========================

Stage 2:
- Categorizes healthcare companies
- Uses:
	1. Rules
	2. Domain hints
	3. Ollama fallback
- Adds confidence scores
"""

import sys
import os
import re
import time
import pandas as pd
import requests

DEFAULT_INPUT = "1_output/company_contacts.csv"

DEFAULT_OUTPUT = "2_output/company_contacts_categorized.csv"

OLLAMA_URL = "http://localhost:11434/api/generate"

OLLAMA_MODEL = "qwen2.5:7b"

REQUEST_TIMEOUT = 90

VALID_CATEGORIES = {
	"Dental",
	"Mental Health / Counseling",
	"Family Medicine / Primary Care",
	"Pediatrics",
	"Chiropractic",
	"Physical Therapy / Rehab",
	"Home Health / Hospice",
	"Hospital / Health System",
	"Specialty Clinic",
	"Urgent Care",
	"Vision / Optometry",
	"Pharmacy / Compounding",
	"Veterinary",

	"Healthcare IT / SaaS",
	"Billing / Revenue Cycle",
	"Staffing / Recruiting",
	"Consulting / Compliance",

	"Non-Profit / Government Health",
	"Wellness / Integrative / Alternative",
	"Substance Abuse / Addiction Recovery",

	"Other Healthcare",
	"Non-Healthcare",

	"Ambiguous / Needs Review",
}

RULES = [

	# Vendors FIRST

	{
		"category": "Healthcare IT / SaaS",
		"keywords": [
			r"\behr\b",
			r"\bemr\b",
			r"\bsoftware\b",
			r"\bplatform\b",
			r"\bsaas\b",
			r"\btech\b",
			r"\bit services\b",
		]
	},

	{
		"category": "Billing / Revenue Cycle",
		"keywords": [
			r"\bbilling\b",
			r"\brevenue cycle\b",
			r"\bcoding\b",
			r"\bmedical billing\b",
		]
	},

	{
		"category": "Staffing / Recruiting",
		"keywords": [
			r"\bstaffing\b",
			r"\brecruiting\b",
			r"\bplacement\b",
		]
	},

	# Providers SECOND

	{
		"category": "Dental",
		"keywords": [
			r"\bdental\b",
			r"\bdentistry\b",
			r"\borthodont",
			r"\bendodont",
			r"\bperiodont",
		]
	},

	{
		"category": "Mental Health / Counseling",
		"keywords": [
			r"\bbehavioral health\b",
			r"\bmental health\b",
			r"\btherapy\b",
			r"\bcounseling\b",
			r"\bpsychiatry\b",
		]
	},

	{
		"category": "Hospital / Health System",
		"keywords": [
			r"\bhospital\b",
			r"\bmedical center\b",
			r"\bhealth system\b",
		]
	},

	{
		"category": "Vision / Optometry",
		"keywords": [
			r"\bvision\b",
			r"\boptometry\b",
			r"\bophthalmology\b",
			r"\beye care\b",
		]
	},
]


def safe_str(value):

	if pd.isna(value):
		return ""

	return str(value).strip()


def classify_by_rules(text):

	text = text.lower()

	for rule in RULES:

		for kw in rule["keywords"]:

			if re.search(kw, text, re.IGNORECASE):
				return rule["category"], 0.98, "rules"

	return None, 0.0, None


def build_context(row):

	parts = []

	fields = [
		("Organization", row.get("company_name")),
		("Domain", row.get("root_domain")),
		("Title", row.get("title")),
		("Role", row.get("role")),
		("Hint", row.get("domain_category_hint")),
	]

	for label, value in fields:

		value = safe_str(value)

		if value:
			parts.append(f"{label}: {value}")

	return " | ".join(parts)


def call_ollama(prompt):

	payload = {
		"model": OLLAMA_MODEL,
		"prompt": prompt,
		"stream": False,
		"options": {
			"temperature": 0,
			"num_predict": 50,
		},
	}

	resp = requests.post(
		OLLAMA_URL,
		json=payload,
		timeout=REQUEST_TIMEOUT
	)

	resp.raise_for_status()

	return resp.json()["response"].strip()


def classify_with_llm(context):

	prompt = f"""
Classify this healthcare-related organization.

Context:
{context}

Allowed Categories:
Dental
Mental Health / Counseling
Family Medicine / Primary Care
Pediatrics
Chiropractic
Physical Therapy / Rehab
Home Health / Hospice
Hospital / Health System
Specialty Clinic
Urgent Care
Vision / Optometry
Pharmacy / Compounding
Veterinary
Healthcare IT / SaaS
Billing / Revenue Cycle
Staffing / Recruiting
Consulting / Compliance
Non-Profit / Government Health
Wellness / Integrative / Alternative
Substance Abuse / Addiction Recovery
Other Healthcare
Non-Healthcare
Ambiguous / Needs Review

Reply ONLY with the category name.
"""

	try:

		resp = call_ollama(prompt)

		resp = resp.strip()

		if resp in VALID_CATEGORIES:
			return resp, 0.80, "llm"

	except Exception:
		pass

	return "Ambiguous / Needs Review", 0.40, "llm"


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

	outfile = os.path.join(
		output_dir,
		"company_contacts_categorized.csv"
	)

	df = pd.read_csv(input_file, low_memory=False)

	print(f"Loaded {len(df):,} rows")

	cache = {}

	categories = []
	confidences = []
	sources = []

	start = time.time()

	for idx, row in df.iterrows():

		cache_key = (
			safe_str(row.get("normalized_org")),
			safe_str(row.get("root_domain")),
		)

		if cache_key in cache:

			category, confidence, source = cache[cache_key]

		else:

			context = build_context(row)

			category, confidence, source = (
				classify_by_rules(context)
			)

			if not category:

				hint = safe_str(
					row.get("domain_category_hint")
				)

				if hint:

					category = hint
					confidence = 0.90
					source = "domain_hint"

			if not category:

				category, confidence, source = (
					classify_with_llm(context)
				)

			cache[cache_key] = (
				category,
				confidence,
				source,
			)

		categories.append(category)
		confidences.append(confidence)
		sources.append(source)

		if idx % 100 == 0:
			print(f"{idx:,}/{len(df):,}")

	df["category"] = categories
	df["category_confidence"] = confidences
	df["category_source"] = sources

	df.to_csv(outfile, index=False)

	print(f"Saved: {outfile}")

	elapsed = time.time() - start

	print(f"Completed in {elapsed/60:.1f} minutes")


if __name__ == "__main__":
	main()