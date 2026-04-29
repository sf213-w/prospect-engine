import pandas as pd
import re
import os

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
INPUT_FILE  = "company_contacts_categorized.csv"
OUTPUT_DIR  = "split_data"   # Change to your desired output folder

CATEGORY_COLUMN = "Category"

CATEGORY_MAP = {
    "mental_health.csv": [
        "Mental Health / Counseling",
        "Substance Abuse / Addiction Recovery",
    ],
    "dental.csv": [
        "Dental",
    ],
    "wellness.csv": [
        "Wellness / Integrative / Alternative",
        "Chiropractic",
        "Physical Therapy / Rehab",
        "Home Health / Hospice",
    ],
    "eye_care.csv": [
        "Vision / Optometry",
    ],
    # Everything not matched above lands here
    "other.csv": None,
}

# ---------------------------------------------------------------------------
# Spam detection helpers
# ---------------------------------------------------------------------------

# First names that are clearly not real people
SPAM_FIRST_NAMES = {
    "hey", "hello", "heey", "hi", "hallo", "heya!", "heya", "hiya",
    "sup!", "good", "howdy", "g'day", "how", "null#", "full",
    "full name", "test", "nope", "null",
}

# Patterns in any text field that indicate spam content
SPAM_CONTENT_PATTERN = re.compile(
    r"(https?://|page\.link|>>>|bf\?|b00ty|sweety|wana be|want to be my|"
    r"profit it|bitcoin|btc.transaction|withdr|g\u043e t\u043e|s\u0435nding|dear\.:)",
    re.IGNORECASE,
)

# Suspicious email domains / patterns
SPAM_EMAIL_PATTERN = re.compile(
    r"(^test|spam|noreply|no-reply|donotreply|example\.com|mailinator|"
    r"guerrillamail|trashmail|yopmail)",
    re.IGNORECASE,
)

# Emails so short they are clearly fake, e.g. w@w.com, a@b.co
FAKE_EMAIL_PATTERN = re.compile(r"^[a-z]{1,2}@[a-z]{1,4}\.[a-z]{2,4}$", re.IGNORECASE)

# Must have exactly one @ and a dot after it
VALID_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _str(value) -> str:
    """Safe string conversion, returns '' for NaN/None."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def is_spam_row(row: pd.Series) -> bool:
    """Return True if the row should be removed as spam / junk."""

    first = _str(row.get("Person - First name"))
    last  = _str(row.get("Person - Last name"))
    email = _str(row.get("Person - Email - Work"))

    # 1. Bounced — undeliverable
    if _str(row.get("Person - Marketing status")) == "Bounced":
        return True

    # 2. Greeting / placeholder first name
    if first.lower() in SPAM_FIRST_NAMES:
        return True

    # 3. Spam content anywhere in name or email fields
    for field in (first, last, email,
                  _str(row.get("Person - Email - Home")),
                  _str(row.get("Person - Email - Other"))):
        if field and SPAM_CONTENT_PATTERN.search(field):
            return True

    # 4. Missing both first AND last name
    if not first and not last:
        return True

    # 5. Work email checks (only when present)
    if email:
        if SPAM_EMAIL_PATTERN.search(email):
            return True
        if FAKE_EMAIL_PATTERN.match(email):
            return True
        if not VALID_EMAIL_PATTERN.match(email):   # malformed, e.g. gmail.com8
            return True

    return False


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
df = pd.read_csv(INPUT_FILE, dtype=str)
original_count = len(df)
print(f"Loaded {original_count:,} rows from '{INPUT_FILE}'")

if CATEGORY_COLUMN not in df.columns:
    raise ValueError(f"Column '{CATEGORY_COLUMN}' not found. Available: {list(df.columns)}")

# ---------------------------------------------------------------------------
# Remove spam
# ---------------------------------------------------------------------------
spam_mask = df.apply(is_spam_row, axis=1)
df_clean = df[~spam_mask].copy()
print(f"Removed {spam_mask.sum():,} spam/junk rows  ->  {len(df_clean):,} rows remaining")

# ---------------------------------------------------------------------------
# Deduplicate
# ---------------------------------------------------------------------------
before_dedup = len(df_clean)

# 1. Drop fully identical rows
df_clean = df_clean.drop_duplicates()

# 2. Deduplicate by work email (skip nulls — null is not a duplicate of null)
#    Among duplicates, keep the row with the most data filled in.
has_work_email = df_clean["Person - Email - Work"].notna()
df_with    = df_clean[has_work_email].copy()
df_without = df_clean[~has_work_email].copy()

df_with["_filled"] = df_with.notna().sum(axis=1)
df_with = (
    df_with
    .sort_values("_filled", ascending=False)
    .drop_duplicates(subset=["Person - Email - Work"], keep="first")
    .drop(columns=["_filled"])
)

df_clean = pd.concat([df_with, df_without], ignore_index=True)

print(f"Removed {before_dedup - len(df_clean):,} duplicate rows  ->  {len(df_clean):,} rows remaining")

# ---------------------------------------------------------------------------
# Split into category files
# ---------------------------------------------------------------------------
df_clean["_cat"] = df_clean[CATEGORY_COLUMN].astype(str).str.strip()
assigned = pd.Series(False, index=df_clean.index)

os.makedirs(OUTPUT_DIR, exist_ok=True)
print()

for filename, values in CATEGORY_MAP.items():
    if values is not None:
        mask   = df_clean["_cat"].isin(values)
        subset = df_clean[mask].drop(columns=["_cat"])
        assigned |= mask
    else:
        subset = df_clean[~assigned].drop(columns=["_cat"])

    out_path = os.path.join(OUTPUT_DIR, filename)
    subset.to_csv(out_path, index=False)
    print(f"  {filename}: {len(subset):,} rows")

print(f"\nDone! Files written to: {os.path.abspath(OUTPUT_DIR)}")