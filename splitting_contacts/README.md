# Contact Segmentation Pipeline
## Two-script workflow for cleaning and categorizing healthcare contacts

---

## Requirements

```bash
pip install pandas requests
```

Ollama must be running with llama3.2 pulled:
```bash
ollama serve           # in a separate terminal
ollama pull llama3.2
```

---

## Step 1 — Split contacts by email type

```bash
python3 1_split_contacts.py raw_data.csv
```

**Outputs (in same folder as input):**
| File | Contents |
|---|---|
| `company_contacts.csv`  | Company / medical practice emails ← campaign list |
| `edu_contacts.csv`      | .edu university/school emails |
| `personal_contacts.csv` | Gmail, Yahoo, Hotmail, etc. |

Custom output directory:
```bash
python3 1_split_contacts.py raw_data.csv ./output/
```

---

## Step 2 — Categorize company contacts with AI

```bash
python3 2_categorize_companies.py company_contacts.csv
```

**Outputs:**
| File | Contents |
|---|---|
| `company_contacts_categorized.csv` | Full list + `Category` column |
| `category_report.csv` | Summary: counts, unique orgs, samples per category |

Custom output directory:
```bash
python3 2_categorize_companies.py company_contacts.csv ./output/
```

---

## Categories used

- Dental
- Mental Health / Counseling
- Family Medicine / Primary Care
- Pediatrics
- Chiropractic
- Physical Therapy / Rehab
- Home Health / Hospice
- Hospital / Health System
- Specialty Clinic
- Urgent Care
- Vision / Optometry
- Pharmacy / Compounding
- Veterinary
- Medical Education / University
- Insurance / Billing / Admin
- Medical Technology / Software
- Non-Profit / Government Health
- Wellness / Integrative / Alternative
- Substance Abuse / Addiction Recovery
- Other Healthcare
- Non-Healthcare

---

## Performance notes

- llama3.2 processes ~30 orgs per batch
- Expect ~2–5 minutes per 1,000 unique organizations
- For ~10,000 unique orgs: plan for 20–50 minutes depending on hardware
- GPU acceleration (if available) will be used automatically by Ollama

## Tuning batch size

If you get errors or timeouts, reduce `BATCH_SIZE` in `2_categorize_companies.py`:
```python
BATCH_SIZE = 15   # more reliable on slower machines
BATCH_SIZE = 50   # faster on GPU/powerful hardware
```
