import pandas as pd

# ============================================
# CONFIG
# ============================================

INPUT_CSV = "split_data/dental.csv"
OUTPUT_CSV = "split_data/collated_emails/dental_emails_prepared.csv"

WORK_COL = "Person - Email - Work"
HOME_COL = "Person - Email - Home"
OTHER_COL = "Person - Email - Other"

# ============================================
# LOAD CSV
# ============================================

print("Loading CSV...")

df = pd.read_csv(INPUT_CSV)

print(f"Loaded {len(df)} rows")

# ============================================
# HELPERS
# ============================================

def clean_email(email):

	if pd.isna(email):
		return None

	email = str(email).strip().lower()

	if email == "":
		return None

	if "@" not in email:
		return None

	return email

def select_best_email(row):

	work = clean_email(row.get(WORK_COL))
	home = clean_email(row.get(HOME_COL))
	other = clean_email(row.get(OTHER_COL))

	# Priority:
	# 1. Work
	# 2. Home
	# 3. Other

	if work:
		return work

	if home:
		return home

	if other:
		return other

	return None

# ============================================
# CREATE MASTER EMAIL COLUMN
# ============================================

print("Selecting best emails...")

df["email"] = df.apply(select_best_email, axis=1)

# Remove rows with no email
df = df[df["email"].notna()]

print(f"Rows with emails: {len(df)}")

# Remove duplicates
before = len(df)

df = df.drop_duplicates(subset=["email"])

after = len(df)

print(f"Removed {before - after} duplicate emails")

# ============================================
# COLUMN MAPPING
# ============================================

COLUMN_MAPPING = {
	"Person - Marketing status": "marketing_status",
	"Person - Double opt-in": "double_opt-in",
	"Person - First name": "first_name",
	"Person - Last name": "last_name",
	"Person - ReferralURL": "refferal_url",
	"Person - Phone - Work": "phone",
	"Organization - Website": "website",
	"Person - Title": "title",
	"Organization - State": "state",
	"Person - Role": "role",
	"Organization - Name": "organization",
	"Organization - LinkedIn URL": "linkedin_company",
	"Organization - Employees": "employees",
	"Company Name": "company_name",
	"Organization - City": "city",
	"Sweet Spot": "sweet_spot",
	"Sales Process Stage": "sales_process_stage",
	"Sample Modules": "sample_modules",
	"Date Created": "date_created",
	"Category": "category"
}

# Rename columns that exist
existing_mapping = {
	old: new
	for old, new in COLUMN_MAPPING.items()
	if old in df.columns
}

df = df.rename(columns=existing_mapping)

# ============================================
# KEEP ONLY DESIRED COLUMNS
# ============================================

FINAL_COLUMNS = [
	"marketing_status",
	"double_opt-in",
	"first_name",
	"last_name",
	"refferal_url",
	"phone",
	"website",
	"title",
	"state",
	"role",
	"organization",
	"linkedin_company",
	"employees",
	"company_name",
	"city",
	"sweet_spot",
	"sales_process_stage",
	"sample_modules",
	"date_created",
	"category",
	"email"
]

# Create any missing columns
for col in FINAL_COLUMNS:

	if col not in df.columns:
		df[col] = ""

# Keep only final columns
df = df[FINAL_COLUMNS]

# ============================================
# SAVE OUTPUT
# ============================================

df.to_csv(
	OUTPUT_CSV,
	index=False
)

print(f"\nSaved cleaned file to: {OUTPUT_CSV}")