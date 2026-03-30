import pandas as pd
import re

INPUT_FILE = "data/people-11381378-107.csv"
OUTPUT_FILE = "data/cleaned_people-11381378-107.csv"

GENERIC_PREFIXES = {
	"info", "admin", "contact", "support", "hello", "office"
}

FREE_EMAIL_DOMAINS = {
	"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"
}


def is_valid_email(email):
	if pd.isna(email):
		return False
	
	email = email.strip().lower()

	# Basic format check
	pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
	if not re.match(pattern, email):
		return False

	# Remove generic prefixes
	prefix = email.split("@")[0]
	if prefix in GENERIC_PREFIXES:
		return False

	return True


def is_free_domain(email):
	domain = email.split("@")[-1]
	return domain in FREE_EMAIL_DOMAINS


def clean_name(name):
	if pd.isna(name):
		return None
	
	name = str(name).strip()

	if name.lower() in ["null", "noname", "", "nan"]:
		return None

	# Capitalize properly
	return name.capitalize()


def extract_first_name(full_name):
	if pd.isna(full_name):
		return None
	
	parts = str(full_name).strip().split()
	if len(parts) > 0:
		return parts[0].capitalize()
	
	return None


def main():
	df = pd.read_csv(INPUT_FILE)

	# Rename columns for easier handling
	df = df.rename(columns={
		"Person - First name": "first_name",
		"Person - Last name": "last_name",
		"Person - Email - Work": "email_work",
		"Person - Email - Home": "email_home",
		"Person - Email - Other": "email_other",
		"Person - Organization": "company",
		"Person - Website": "website",
		"Person - Title": "title",
		"Person - City": "city",
		"Person - State": "state",
		"Person - Name": "full_name"
	})

	# Combine emails (priority: work > home > other)
	df["email"] = df["email_work"]
	df["email"] = df["email"].fillna(df["email_home"])
	df["email"] = df["email"].fillna(df["email_other"])

	# Clean email formatting
	df["email"] = df["email"].astype(str).str.strip().str.lower()

	# Remove invalid emails
	df = df[df["email"].apply(is_valid_email)]

	# Remove free domains (optional – comment out if needed)
	df = df[~df["email"].apply(is_free_domain)]

	# Clean names
	df["first_name"] = df["first_name"].apply(clean_name)
	df["last_name"] = df["last_name"].apply(clean_name)

	# Fill missing first name from full name
	df["first_name"] = df.apply(
		lambda row: row["first_name"] if pd.notna(row["first_name"]) else extract_first_name(row["full_name"]),
		axis=1
	)

	# Create safe fallback for personalization
	df["first_name_clean"] = df["first_name"].fillna("there")

	# Clean company field
	if "company" in df.columns:
		df["company"] = df["company"].astype(str).str.strip()

	# Deduplicate by email
	df = df.drop_duplicates(subset=["email"])

	# Final column selection (Woodpecker-friendly)
	output_columns = [
		"first_name_clean",
		"first_name",
		"last_name",
		"email",
		"company",
		"website",
		"title",
		"city",
		"state"
	]

	# Keep only existing columns
	output_columns = [col for col in output_columns if col in df.columns]

	df = df[output_columns]

	# Save output
	df.to_csv(OUTPUT_FILE, index=False)

	print(f"Cleaned file saved to {OUTPUT_FILE}")
	print(f"Total contacts: {len(df)}")


if __name__ == "__main__":
	main()