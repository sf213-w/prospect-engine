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
# SAVE OUTPUT
# ============================================

df.to_csv(
	OUTPUT_CSV,
	index=False
)

print(f"\nSaved cleaned file to: {OUTPUT_CSV}")