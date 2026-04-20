"""
1_split_contacts.py
====================
Splits a contacts CSV into three files based on email type:
  - edu_contacts.csv       → .edu addresses
  - personal_contacts.csv  → Gmail, Yahoo, Hotmail, etc.
  - company_contacts.csv   → Company / medical practice emails (the campaign-ready list)

Usage:
  python3 1_split_contacts.py                          # uses default input below
  python3 1_split_contacts.py my_contacts.csv          # custom input file
  python3 1_split_contacts.py contacts.csv output_dir/ # custom input + output dir
"""

import sys
import os
import pandas as pd

# ── Configuration ──────────────────────────────────────────────────────────────
DEFAULT_INPUT = "raw_data.csv"

EMAIL_COLUMNS = [
    "Person - Email - Work",
    "Person - Email - Home",
    "Person - Email - Other",
]

PERSONAL_DOMAINS = {
    # Google
    "gmail.com", "googlemail.com",
    # Yahoo
    "yahoo.com", "yahoo.co.uk", "yahoo.co.in", "yahoo.com.au",
    "yahoo.ca", "yahoo.fr", "yahoo.de", "yahoo.es", "yahoo.it",
    "ymail.com", "rocketmail.com",
    # Microsoft
    "hotmail.com", "hotmail.co.uk", "hotmail.fr", "hotmail.de",
    "outlook.com", "outlook.co.uk", "live.com", "live.co.uk",
    "live.ca", "msn.com", "passport.com",
    # Apple
    "icloud.com", "me.com", "mac.com",
    # AOL / Verizon
    "aol.com", "aim.com", "verizon.net",
    # Privacy / Other consumer
    "protonmail.com", "proton.me", "tutanota.com", "tutamail.com",
    "zoho.com", "mail.com", "gmx.com", "gmx.net", "gmx.de",
    # US ISP
    "comcast.net", "sbcglobal.net", "att.net", "cox.net",
    "earthlink.net", "bellsouth.net", "charter.net", "optonline.net",
    # Other common consumer
    "me.com", "inbox.com",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_primary_email(row):
    """Return the first non-empty email value across the email columns."""
    for col in EMAIL_COLUMNS:
        val = row.get(col, "")
        if pd.notna(val) and str(val).strip():
            return str(val).strip().lower()
    return None


def classify_email(email):
    if not isinstance(email, str) or not email:
        return "no_email"
    domain = email.split("@")[-1] if "@" in email else ""
    if domain.endswith(".edu") or ".edu." in domain:
        return "edu"
    if domain in PERSONAL_DOMAINS:
        return "personal"
    return "company"


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    # --- Parse args ---
    input_file  = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    output_dir  = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(input_file) or "."
    os.makedirs(output_dir, exist_ok=True)

    out_edu      = os.path.join(output_dir, "edu_contacts.csv")
    out_personal = os.path.join(output_dir, "personal_contacts.csv")
    out_company  = os.path.join(output_dir, "company_contacts.csv")

    # --- Load ---
    print(f"Loading: {input_file}")
    df = pd.read_csv(input_file, low_memory=False)
    print(f"  {len(df):,} total rows\n")

    # --- Classify ---
    df["_primary_email"] = df.apply(get_primary_email, axis=1)
    df["_email_type"]    = df["_primary_email"].apply(classify_email)

    edu_df      = df[df["_email_type"] == "edu"].drop(columns=["_primary_email", "_email_type"])
    personal_df = df[df["_email_type"] == "personal"].drop(columns=["_primary_email", "_email_type"])
    company_df  = df[df["_email_type"] == "company"].drop(columns=["_primary_email", "_email_type"])
    no_email_df = df[df["_email_type"] == "no_email"]

    # --- Save ---
    edu_df.to_csv(out_edu, index=False)
    personal_df.to_csv(out_personal, index=False)
    company_df.to_csv(out_company, index=False)

    # --- Report ---
    total = len(df)
    print("✅ Split complete:")
    print(f"   {out_company:<45} {len(company_df):>7,} rows  ({len(company_df)/total*100:.1f}%)")
    print(f"   {out_edu:<45} {len(edu_df):>7,} rows  ({len(edu_df)/total*100:.1f}%)")
    print(f"   {out_personal:<45} {len(personal_df):>7,} rows  ({len(personal_df)/total*100:.1f}%)")
    print(f"   (no email — excluded)                       {len(no_email_df):>7,} rows  ({len(no_email_df)/total*100:.1f}%)")
    print(f"\n   Total accounted for: {total:,} / {total:,}")
    print(f"\n▶ Next step: python3 2_categorize_companies.py {out_company}")


if __name__ == "__main__":
    main()
