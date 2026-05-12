"""
2_categorize_companies.py
==========================
Uses a local Ollama model (llama3.2) to classify each unique organization in
company_contacts.csv into a healthcare category, then produces:
  - company_contacts_categorized.csv   full list + "Category" column
  - category_report.csv                summary: counts, unique orgs, samples
  - categorize_progress.json           auto-saved progress (safe to Ctrl+C and resume)

Usage:
  python 2_categorize_companies.py                               # default input
  python 2_categorize_companies.py company_contacts.csv         # custom input
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
DEFAULT_INPUT    = "company_contacts.csv"
OLLAMA_URL       = "http://localhost:11434/api/generate"
OLLAMA_MODEL     = "llama3.2"
BATCH_SIZE       = 5      # very small — keeps prompts short, avoids 500s
RETRY_LIMIT      = 3      # retries per batch before one-by-one fallback
RETRY_DELAY      = 3      # seconds between retries (give Ollama time to recover)
REQUEST_TIMEOUT  = 90     # seconds per call
PROGRESS_FILE    = "categorize_progress.json"   # resume from here if interrupted

EMAIL_COLUMNS = [
    "Person - Email - Work",
    "Person - Email - Home",
    "Person - Email - Other",
]

# Short codes shown in the prompt to keep token count low.
# Mapped back to full names after the LLM responds.
CODE_TO_CATEGORY = {
    "1":  "Dental",
    "2":  "Mental Health / Counseling",
    "3":  "Family Medicine / Primary Care",
    "4":  "Pediatrics",
    "5":  "Chiropractic",
    "6":  "Physical Therapy / Rehab",
    "7":  "Home Health / Hospice",
    "8":  "Hospital / Health System",
    "9":  "Specialty Clinic",
    "10": "Urgent Care",
    "11": "Vision / Optometry",
    "12": "Pharmacy / Compounding",
    "13": "Veterinary",
    "14": "Medical Education / University",
    "15": "Business Associate",
    "16": "Insurance / Billing / Admin",
    "17": "Medical Technology / Software",
    "18": "Non-Profit / Government Health",
    "19": "Wellness / Integrative / Alternative",
    "20": "Substance Abuse / Addiction Recovery",
    "21": "Other Healthcare",
    "22": "Non-Healthcare",
}

CATEGORIES = list(CODE_TO_CATEGORY.values())

# Build reverse map for normalize_category
CATEGORY_LOWER = {c.lower(): c for c in CATEGORIES}


# ── Prompts ────────────────────────────────────────────────────────────────────
# Use numbered codes to keep the prompt very short and avoid context overflow.

CATEGORY_LEGEND = "\n".join(f"{k}={v}" for k, v in CODE_TO_CATEGORY.items())

# Business Associate note kept brief
BA_NOTE = "15=Business Associate (serves healthcare: billing, IT, EHR, staffing, transcription, consulting)"


def make_batch_prompt(orgs):
    n = len(orgs)
    numbered = "\n".join(f"{i+1}. {org}" for i, org in enumerate(orgs))
    return f"""Classify each organization. Reply with a JSON array of {n} category codes (numbers only).

Codes:
{CATEGORY_LEGEND}
{BA_NOTE}
22=Non-Healthcare (no healthcare connection at all)

Organizations:
{numbered}

Reply with ONLY a JSON array of {n} numbers. Example for 3 orgs: [3,15,22]
Output:"""


def make_single_prompt(org):
    return f"""Classify this organization using a category code number.

Codes:
{CATEGORY_LEGEND}
{BA_NOTE}

Organization: {org}

Reply with ONLY the number. Output:"""


# ── Ollama interface ───────────────────────────────────────────────────────────

def _call_ollama(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": 80,   # codes are short — no need for more tokens
            "top_p": 1,
        },
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
    if resp.status_code == 500:
        # Extract Ollama's error message for better diagnostics
        try:
            detail = resp.json().get("error", resp.text[:200])
        except Exception:
            detail = resp.text[:200]
        raise RuntimeError(f"Ollama 500: {detail}")
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def parse_codes(text, expected):
    """Extract a list of numeric category codes from the LLM response."""
    text = re.sub(r"```[a-z]*\n?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```", "", text).strip()
    # Find a [...] block first
    match = re.search(r"\[([^\]]+)\]", text)
    if match:
        raw = match.group(1)
    else:
        # Fall back: grab all digit sequences
        raw = text
    codes = re.findall(r"\d+", raw)
    if len(codes) != expected:
        raise ValueError(f"Expected {expected} codes, got {len(codes)} from: {text[:150]}")
    return codes


def code_to_cat(code):
    """Map a numeric string code to a full category name."""
    return CODE_TO_CATEGORY.get(str(code).strip(), "Other Healthcare")


def normalize_category(raw):
    """Fuzzy-match a raw string to the nearest valid category."""
    raw = str(raw).strip().strip('"').strip("'")
    if raw in CATEGORIES:
        return raw
    if raw.lower() in CATEGORY_LOWER:
        return CATEGORY_LOWER[raw.lower()]
    for cat in CATEGORIES:
        if raw.lower() in cat.lower() or cat.lower() in raw.lower():
            return cat
    return "Other Healthcare"


# ── Classification logic ───────────────────────────────────────────────────────

def classify_one(org):
    """Single-org fallback — tiny prompt, extremely reliable."""
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            raw = _call_ollama(make_single_prompt(org))
            # Could be a number or a category name
            codes = re.findall(r"\d+", raw)
            if codes:
                return code_to_cat(codes[0])
            return normalize_category(raw)
        except Exception as e:
            if attempt < RETRY_LIMIT:
                time.sleep(RETRY_DELAY)
    return "Other Healthcare"


def classify_batch(orgs):
    """
    Batch classify with retries. Falls back to one-by-one on persistent failure.
    """
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            raw   = _call_ollama(make_batch_prompt(orgs))
            codes = parse_codes(raw, len(orgs))
            return [code_to_cat(c) for c in codes]
        except Exception as e:
            if attempt < RETRY_LIMIT:
                print(f"\n    ↺ Retry {attempt}/{RETRY_LIMIT-1}: {e}", end=" ", flush=True)
                time.sleep(RETRY_DELAY)
            else:
                print(f"\n    ↳ Falling back to one-by-one ...", flush=True)
                return [classify_one(org) for org in orgs]


# ── Progress save/load ─────────────────────────────────────────────────────────

def load_progress(path):
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
            print(f"  Resuming from saved progress: {len(data):,} orgs already done.")
            return data
        except Exception:
            pass
    return {}


def save_progress(path, mapping):
    # Write to temp file first then rename — prevents corrupt save if killed mid-write
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(mapping, f)
    os.replace(tmp, path)


# ── Core pipeline ──────────────────────────────────────────────────────────────

def categorize_all(unique_orgs, progress_path):
    import signal

    mapping      = load_progress(progress_path)
    already_done = len(mapping)          # snapshot — fixed for percentage math
    remaining    = [o for o in unique_orgs if o not in mapping]
    total        = len(unique_orgs)      # grand total, never changes

    if not remaining:
        print("  All orgs already categorized from saved progress.")
        return mapping

    batches   = [remaining[i : i + BATCH_SIZE] for i in range(0, len(remaining), BATCH_SIZE)]
    processed = 0                        # only counts orgs done THIS run

    def _save_and_exit(sig=None, frame=None):
        print("\nCtrl+C — saving progress, please wait ...", flush=True)
        save_progress(progress_path, mapping)
        print(f"Saved to: {progress_path}")
        print("Re-run the script to resume.")
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _save_and_exit)

    try:
        for idx, batch in enumerate(batches, 1):
            processed += len(batch)
            done_total = already_done + processed   # always accurate
            pct        = done_total / total * 100
            print(
                f"  [{pct:5.1f}%]  Batch {idx}/{len(batches)}  "
                f"({done_total}/{total}) ...",
                end=" ", flush=True,
            )
            cats = classify_batch(batch)
            for org, cat in zip(batch, cats):
                mapping[org] = cat
            print("✓", flush=True)

            # Save every 10 batches — small cost, big safety net
            if idx % 10 == 0:
                save_progress(progress_path, mapping)

    finally:
        # Always save on any exit — crash, error, or normal finish
        save_progress(progress_path, mapping)

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
    input_file    = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    output_dir    = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(input_file))
    os.makedirs(output_dir, exist_ok=True)

    out_full      = os.path.join(output_dir, "company_contacts_categorized.csv")
    out_report    = os.path.join(output_dir, "category_report.csv")
    progress_path = os.path.join(output_dir, PROGRESS_FILE)

    check_ollama()

    print(f"\nLoading: {input_file}")
    df = pd.read_csv(input_file, low_memory=False)
    print(f"  {len(df):,} rows loaded.")

    df["_org"]   = df.apply(best_org_name, axis=1)
    unique_orgs  = [o for o in df["_org"].unique() if o != "Unknown"]
    n_batches    = (len(unique_orgs) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"  {len(unique_orgs):,} unique organizations -> {n_batches} batches of up to {BATCH_SIZE}")
    print(f"  Progress saves to: {progress_path}  (safe to Ctrl+C and re-run to resume)\n")

    print("Categorizing with Ollama (llama3.2)...")
    t0         = time.time()
    org_to_cat = categorize_all(unique_orgs, progress_path)
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

    # Clean up progress file on successful completion
    if os.path.exists(progress_path):
        os.remove(progress_path)
        print(f"(Progress file removed — run complete.)")


if __name__ == "__main__":
    main()