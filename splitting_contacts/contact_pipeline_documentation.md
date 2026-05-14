# Contact Pipeline Documentation

## The Big Picture

You start with one big raw spreadsheet of contacts (`raw_data.csv`) and end up with several clean, organized lists sorted by type of business. The three scripts run in order, each one handing off to the next.

---

## Program 1 — Sort the Contacts (`1_split_contacts.py`)

**What it does:** Takes the messy raw spreadsheet and does some initial housekeeping before splitting everyone into buckets.

### Step by Step

- **Cleans up column names** — the original spreadsheet has long, awkward column names like "Person - First name." This renames them to simple ones like `first_name`.

- **Picks the best email** — each person might have a work email, home email, and "other" email. It picks whichever one exists, in that priority order.

- **Figures out the email domain** — for `jane@acmedental.com`, it pulls out `acmedental.com`. This domain is used as a clue about what kind of organization it is.

- **Scores contact quality** — marks each contact as *high*, *medium*, or *low* quality. A real personal email is high quality; a generic inbox like `info@company.com` is medium; no email at all is low.

- **Removes duplicates** — if the same email appears more than once, it keeps only the first one.

- **Splits into five output files:**

| File | Who's in it |
|---|---|
| `company_contacts.csv` | Real business emails |
| `personal_contacts.csv` | Gmail, Yahoo, Hotmail, etc. |
| `edu_contacts.csv` | University/college emails (.edu) |
| `student_contacts.csv` | School districts, K-12 |
| `invalid_contacts.csv` | Missing or broken emails |

---

## Program 2 — Label Each Company (`2_categorize_companies.py`)

**What it does:** Takes the business contacts and figures out what *type* of healthcare business each one is (dental office, mental health clinic, hospital, etc.).

### It tries three methods in order, stopping when one works:

1. **Simple keyword matching** — if the company name contains words like "dental," "orthodont," or "oral surgery," it's labeled *Dental*. Fast and reliable when the name is obvious.

2. **Domain name clues** — if the keyword check fails, it looks at the website domain for hints. A domain containing "rehab" or "therapy" gives it away.

3. **AI fallback** — if neither of the above works, it sends the contact info to a locally-running AI model (Ollama) and asks it to make a judgment call. This is slower but handles unusual or ambiguous cases.

### Each contact gets:

- A **category** (e.g. "Dental", "Veterinary", "Mental Health / Counseling")
- A **confidence score** (0–1, where 1 is very confident)
- A **source** (was it figured out by keywords, domain, or AI?)

The full list of possible categories includes things like *Urgent Care*, *Pharmacy*, *Billing / Revenue Cycle*, *Non-Healthcare*, and more.

**Output:** `company_contacts_categorized.csv` plus a summary report of how many contacts landed in each category.

---

## Program 3 — Final Cleanup and Split (`3_split_and_clean.py`)

**What it does:** Takes the categorized contacts, removes anything still problematic, and produces the final, ready-to-use files.

### Step by Step

- **Removes junk** — drops anyone with a missing, malformed, or fake/spam email address (e.g. `@mailinator.com`).

- **Sets aside uncertain ones** — any contact where the AI wasn't very confident (below 50% confidence) or was labeled "Ambiguous / Needs Review" gets moved to a separate `needs_review.csv` file for a human to look at.

- **Deduplicates again more carefully** — first removes exact duplicates, then removes same-email duplicates (keeping the highest-confidence one), then removes people with the same name at the same company.

- **Splits into market segments** — divides the clean contacts into focused lists by business type:

| File | Categories Included |
|---|---|
| `mental_health.csv` | Mental health clinics, addiction recovery |
| `dental.csv` | Dental offices |
| `wellness.csv` | Chiropractic, physical therapy, home health, wellness |
| `eye_care.csv` | Optometry / vision care |
| `other.csv` | Everything that doesn't fit the above |

- **Produces a final report** (`market_report.csv`) — a summary table showing how many contacts and companies ended up in each category, along with the average confidence score.

---

## How They Connect

```
raw_data.csv
     ↓
  Script 1  →  company_contacts.csv (+ personal, edu, student, invalid)
     ↓
  Script 2  →  company_contacts_categorized.csv
     ↓
  Script 3  →  dental.csv, mental_health.csv, wellness.csv, eye_care.csv, other.csv, needs_review.csv
```

The end result is a clean, segmented contact list — ready for targeted outreach to specific types of healthcare businesses.
