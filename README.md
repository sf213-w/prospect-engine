# prospect-engine

> A pipeline for harvesting HIPAA Privacy Officer contact information from healthcare providers listed on the HHS OCR Breach Portal.

---

## Overview

The HHS Office for Civil Rights publishes a public breach report — commonly called the "Wall of Shame" — listing healthcare organizations that have reported data breaches affecting 500 or more individuals. **prospect-engine** ingests that list, filters for Healthcare Providers, and attempts to locate a privacy officer email or phone number for each organization by crawling their official website and running targeted web searches.

The output is a timestamped CSV suitable for downstream outreach, compliance research, or data enrichment workflows.

---

## Features

- Automated scraping of the HHS OCR breach portal using a headless Chromium browser (Playwright)
- DuckDuckGo-powered site discovery with smart filtering of aggregator and social media domains
- Multi-strategy contact extraction: site crawl across common privacy URL paths with fallback to web search
- Incremental CSV output — partial results are preserved if the run is interrupted
- Configurable provider count and pagination limits
- Designed to be modular — swap the input source without touching the contact-finding logic

---

## Tech Stack

- **Python 3.8+**
- [Playwright](https://playwright.dev/python/) — headless Chromium for portal scraping
- [Requests](https://docs.python-requests.org/) — HTTP fetching for site crawls
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) — HTML parsing and contact extraction
- [duckduckgo-search](https://github.com/deedy5/duckduckgo_search) — site discovery and fallback search

---

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip

### Installation

```bash
pip install playwright requests beautifulsoup4 duckduckgo-search
playwright install chromium
```

### Configuration

Open `pipeline/npp_scraper.py` and edit the constants near the top of the file:

```python
TARGET_COUNT = 100   # How many providers to collect
MAX_PAGES    = 10    # Maximum portal pages to paginate through
```

### Run

```bash
python pipeline/npp_scraper.py
```

No arguments required. Output is written to a timestamped CSV in the working directory:

```
privacy_contacts_20260504_110809.csv
```

---

## How It Works

The pipeline runs in three sequential stages:

**1. Ingest — HHS Portal Scrape**
A headless Chromium browser loads the HHS OCR breach report table, paginates through results, and collects up to `TARGET_COUNT` Healthcare Provider names.

**2. Site Discovery — DuckDuckGo Search**
For each provider, the tool queries DuckDuckGo to find the organization's official website. It filters out known aggregator and social media domains (LinkedIn, Healthgrades, Yelp, etc.) and returns the base URL of the best candidate.

**3. Contact Extraction — Site Crawl + Fallback Web Search**
The tool walks a list of known privacy-related URL paths (`/privacy`, `/hipaa`, `/contact-us`, etc.) on the discovered site, scanning page text for email addresses and phone numbers near keywords like "privacy officer," "compliance officer," or "HIPAA." If nothing is found on-site, it falls back to a direct DuckDuckGo search for `"[provider name]" "privacy officer" email contact`.

---

## Output Format

Each row in the CSV corresponds to one provider:

| Field             | Description                                               |
|-------------------|-----------------------------------------------------------|
| `provider_name`   | Name as it appears on the HHS portal                      |
| `website`         | Base URL of the discovered official site                  |
| `emails`          | Semicolon-separated list of email addresses found         |
| `phones`          | Semicolon-separated list of phone numbers found           |
| `source_url`      | The specific page where contact info was located          |
| `context_snippet` | Up to 300 characters of surrounding text for verification |
| `found_via`       | `site crawl`, `web search`, or `not found`                |

Providers with no contact information still appear in the CSV with `found_via = "not found"` and blank contact fields — the output always covers every input provider.

---

## Project Structure

```
prospect-engine/
├── pipeline/               # Core scraper and pipeline scripts
├── breach_dashboard/       # Dashboard for visualizing breach data
├── splitting_contacts/     # Utilities for splitting/segmenting contact output
├── neverbounce_data/       # Email validation data (NeverBounce integration)
├── llm-schema-test/        # LLM schema experiments
├── rc-csv-work/            # CSV processing utilities
├── data/                   # Raw and intermediate data files
├── PRD/                    # Product requirements documentation
├── appendix/               # Supplementary reference material
├── notes/                  # Development notes
├── old/                    # Archived scripts
├── claude-skill/           # Claude skill definitions
├── hipaa_marketing_pipeline_architecture.svg  # Architecture diagram
├── test.csv                # Sample test data
└── .gitignore
```

---

## Performance

The pipeline is sequential and rate-conscious. Each provider requires multiple DuckDuckGo queries and HTTP fetches, so expect roughly **30–90 seconds per provider** depending on site responsiveness. A full 100-provider run typically takes **1–3 hours**.

For parallel execution, the per-provider block in `main()` is a natural unit to wrap with `concurrent.futures.ThreadPoolExecutor`. Add randomized delays between DuckDuckGo calls to avoid throttling.

---

## Known Limitations

- **Website misidentification** — DuckDuckGo occasionally returns an aggregator or third-party vendor instead of the provider's own domain. Always verify `source_url` and `context_snippet` before using contact data.
- **Email false positives** — The regex may capture webmaster addresses or third-party service contacts near privacy keywords.
- **Dynamic pages** — Contact extraction uses plain HTTP + BeautifulSoup. JavaScript-rendered pages will not be fully parsed.
- **DDG rate limits** — DuckDuckGo may throttle requests during long runs. Errors are caught and logged; the pipeline skips the affected query and continues.

---

## Adapting to Other Use Cases

- **Different input source** — `get_healthcare_providers()` is fully decoupled. Replace it with any function returning a list of organization name strings.
- **Different privacy keyword patterns** — Edit the `context_patterns` list in `extract_privacy_contact()` for non-HIPAA regulatory contexts (GDPR, state AG contacts, etc.).
- **Different URL paths** — Extend or replace `PRIVACY_PATHS` to match URL conventions in your target sector.
- **Domain blocklist** — Add domains polluting your results to `BAD_DOMAINS`, or remove entries that are authoritative for your use case.

---

## License

This tool is intended for research and compliance use. Respect the terms of service of any website you crawl. Contact data collected should be used in accordance with applicable law.
