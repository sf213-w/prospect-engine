"""
2_categorize_companies.py
==========================
Uses a local Ollama model (llama3.2) to classify each unique organization in
company_contacts.csv into a healthcare category, then produces:
  - company_contacts_categorized.csv   full list + "Category" column
  - category_report.csv                summary: counts, unique orgs, samples

Usage:
  python 2_categorize_companies.py                              # default input
  python 2_categorize_companies.py company_contacts.csv        # custom input
  python 2_categorize_companies.py company_contacts.csv output/ # + output dir

Requirements:
  pip install pandas requests
  ollama serve          # must be running in a separate terminal
  ollama pull llama3.2  # model must be pulled
"""

import sys
import os
import json
import re
import time
import pandas as pd
import requests

# ── Configuration ──────────────────────────────────────────────────────────────
DEFAULT_INPUT   = "company_contacts.csv"
OLLAMA_URL      = "http://localhost:11434/api/generate"
OLLAMA_MODEL    = "llama3.2"
BATCH_SIZE      = 10     # llama3.2 is a small model — keep batches small and reliable
RETRY_LIMIT     = 2      # retries before falling back to one-by-one
RETRY_DELAY     = 1      # seconds between retries
REQUEST_TIMEOUT = 120    # seconds per Ollama call

EMAIL_COLUMNS = [
    "Person - Email - Work",
    "Person - Email - Home",
    "Person - Email - Other",
]

CATEGORIES = [
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
    "Medical Education / University",
    "Insurance / Billing / Admin",
    "Medical Technology / Software",
    "Non-Profit / Government Health",
    "Wellness / Integrative / Alternative",
    "Substance Abuse / Addiction Recovery",
    "Other Healthcare",
    "Non-Healthcare",
]


# ── Prompts ────────────────────────────────────────────────────────────────────

def make_batch_prompt(orgs):
    numbered = "\n".join(f"{i+1}. {org}" for i, org in enumerate(orgs))
    cat_list  = "\n".join(f"- {c}" for c in CATEGORIES)
    n = len(orgs)
    return f"""Classify each numbered organization into exactly one category.

CATEGORIES:
{cat_list}

ORGANIZATIONS:
{numbered}

Rules:
- Output ONLY a JSON array with exactly {n} strings, one per organization, in order.
- Use the exact category name from the list above.
- Non-healthcare companies -> "Non-Healthcare"
- Unknown or ambiguous healthcare -> "Other Healthcare"
- No explanation, no markdown, no extra text.

Output (JSON array of exactly {n} strings):"""


def make_single_prompt(org):
    cat_list = "\n".join(f"- {c}" for c in CATEGORIES)
    return f"""What category does this organization belong to?

Organization: {org}

CATEGORIES:
{cat_list}

Reply with ONLY the exact category name. No explanation, no punctuation, nothing else.

Category:"""


# ── Ollama interface ───────────────────────────────────────────────────────────

def _call_ollama(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": 400,
            "top_p": 1,
        },
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def parse_batch_response(text, expected):
    text = re.sub(r"```[a-z]*\n?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```", "", text).strip()
    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON array found. Got:\n{text[:200]}")
    arr = json.loads(match.group())
    if not isinstance(arr, list):
        raise ValueError("Parsed value is not a list")
    if len(arr) != expected:
        raise ValueError(f"Expected {expected} items, got {len(arr)}")
    return arr


def normalize_category(raw):
    raw = str(raw).strip().strip('"').strip("'")
    if raw in CATEGORIES:
        return raw
    lower_map = {c.lower(): c for c in CATEGORIES}
    if raw.lower() in lower_map:
        return lower_map[raw.lower()]
    for cat in CATEGORIES:
        if raw.lower() in cat.lower() or cat.lower() in raw.lower():
            return cat
    return "Other Healthcare"


def classify_one(org):
    """Single-org fallback — much simpler prompt, much more reliable."""
    try:
        raw = _call_ollama(make_single_prompt(org))
        return normalize_category(raw)
    except Exception:
        return "Other Healthcare"


def classify_batch(orgs):
    """
    Try batch classification with retries.
    On persistent failure fall back to one-by-one (slower but always works).
    """
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            raw  = _call_ollama(make_batch_prompt(orgs))
            cats = parse_batch_response(raw, len(orgs))
            return [normalize_category(c) for c in cats]
        except Exception as e:
            if attempt < RETRY_LIMIT:
                print(f"\n    ↺ Retry {attempt}: {e}", end=" ", flush=True)
                time.sleep(RETRY_DELAY)
            else:
                print(f"\n    ↳ Batch unstable — falling back to one-by-one ...", flush=True)
                return [classify_one(org) for org in orgs]


# ── Core pipeline ──────────────────────────────────────────────────────────────

def categorize_all(unique_orgs):
    mapping  = {}
    total    = len(unique_orgs)
    batches  = [unique_orgs[i : i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
    processed = 0

    for idx, batch in enumerate(batches, 1):
        processed += len(batch)
        pct = processed / total * 100
        print(f"  [{pct:5.1f}%]  Batch {idx}/{len(batches)}  ({processed}/{total}) ...",
              end=" ", flush=True)
        cats = classify_batch(batch)
        for org, cat in zip(batch, cats):
            mapping[org] = cat
        print("✓", flush=True)

    return mapping


# ── Misc helpers ───────────────────────────────────────────────────────────────

def check_ollama():
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        resp.raise_for_status()
        models    = [m["name"] for m in resp.json().get("models", [])]
        available = [m for m in models if OLLAMA_MODEL.split(":")[0] in m]
        if not available:
            print(f"Model '{OLLAMA_MODEL}' not found. Available: {models}")
            print(f"Run: ollama pull {OLLAMA_MODEL}")
            sys.exit(1)
        print(f"Ollama running  |  Model: {available[0]}")
    except requests.exceptions.ConnectionError:
        print("Cannot connect to Ollama at http://localhost:11434")
        print("Start it first with: ollama serve")
        sys.exit(1)


def get_primary_email(row):
    for col in EMAIL_COLUMNS:
        val = row.get(col, "")
        if pd.notna(val) and str(val).strip():
            return str(val).strip().lower()
    return None


def best_org_name(row):
    for col in ["Person - CompanyName", "Person - Organization"]:
        val = row.get(col, "")
        if pd.notna(val) and str(val).strip():
            return str(val).strip()
    email = get_primary_email(row)
    if email and "@" in email:
        return email.split("@")[1]
    return "Unknown"


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(input_file))
    os.makedirs(output_dir, exist_ok=True)

    out_full   = os.path.join(output_dir, "company_contacts_categorized.csv")
    out_report = os.path.join(output_dir, "category_report.csv")

    check_ollama()

    print(f"\nLoading: {input_file}")
    df = pd.read_csv(input_file, low_memory=False)
    print(f"  {len(df):,} rows loaded.")

    df["_org"]  = df.apply(best_org_name, axis=1)
    unique_orgs = [o for o in df["_org"].unique() if o != "Unknown"]
    n_batches   = (len(unique_orgs) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"  {len(unique_orgs):,} unique organizations -> {n_batches} batches of up to {BATCH_SIZE}\n")

    print("Categorizing with Ollama (llama3.2)...")
    t0         = time.time()
    org_to_cat = categorize_all(unique_orgs)
    elapsed    = time.time() - t0
    print(f"\nFinished in {elapsed/60:.1f} min  ({elapsed/max(len(unique_orgs),1)*1000:.0f} ms/org)\n")

    df["Category"] = df["_org"].map(org_to_cat).fillna("Other Healthcare")
    df = df.drop(columns=["_org"])
    df.to_csv(out_full, index=False)
    print(f"Saved: {out_full}  ({len(df):,} rows)")

    report = (
        df.groupby("Category")
          .agg(
              Contact_Count = ("Category",            "count"),
              Unique_Orgs   = ("Person - CompanyName", lambda x: int(x.nunique())),
              Sample_Orgs   = ("Person - CompanyName", lambda x: " | ".join(
                                   sorted(x.dropna().unique())[:5]))
          )
          .reset_index()
          .sort_values("Contact_Count", ascending=False)
    )
    report.to_csv(out_report, index=False)
    print(f"Saved: {out_report}\n")

    w1, w2, w3 = 40, 10, 12
    sep = "  " + "-" * (w1 + w2 + w3 + 2)
    print("── Category Breakdown " + "─" * (w1 + w2 + w3 - 18))
    print(f"  {'Category':<{w1}} {'Contacts':>{w2}}  {'Unique Orgs':>{w3}}")
    print(sep)
    for _, row in report.iterrows():
        print(f"  {row['Category']:<{w1}} {row['Contact_Count']:>{w2},}  {row['Unique_Orgs']:>{w3},}")
    print(sep)
    print(f"  {'TOTAL':<{w1}} {report['Contact_Count'].sum():>{w2},}  {report['Unique_Orgs'].sum():>{w3},}")
    print()


if __name__ == "__main__":
    main()
