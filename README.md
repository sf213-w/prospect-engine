# NPP Privacy Contact Scraper

A pipeline for harvesting HIPAA Privacy Officer contact information from healthcare providers listed on the HHS OCR Breach Portal.

---

## Overview

The HHS Office for Civil Rights publishes a public breach report — sometimes called the "Wall of Shame" — listing healthcare organizations that have reported data breaches affecting 500 or more individuals. This tool ingests that list, filters for Healthcare Providers, and then attempts to locate a privacy officer email or phone number for each one by crawling their official website and running targeted web searches.

The output is a timestamped CSV suitable for downstream outreach, compliance research, or data enrichment workflows.

---

## How It Works

The pipeline runs in three stages:

**1. Ingest — HHS Portal Scrape**  
A headless Chromium browser (via Playwright) loads the HHS OCR breach report table, pages through results, and collects up to `TARGET_COUNT` (default: 100) Healthcare Provider names.

**2. Site Discovery — DuckDuckGo Search**  
For each provider, the tool queries DuckDuckGo to find the organization's official website. It filters out known aggregator and social media domains (LinkedIn, Healthgrades, Yelp, etc.) and returns the base URL of the best candidate.

**3. Contact Extraction — Site Crawl + Fallback Web Search**  
The tool walks a list of known privacy-related URL paths (`/privacy`, `/hipaa`, `/contact-us`, etc.) on the discovered site and scans page text for email addresses and phone numbers appearing near keywords like "privacy officer," "compliance officer," or "HIPAA." If nothing is found on-site, it falls back to a direct DuckDuckGo search for `"[provider name]" "privacy officer" email contact`.

Results are written to the CSV incrementally — one row per provider — so partial output is preserved if the run is interrupted.

---

## Requirements

```
Python 3.8+
playwright
requests
beautifulsoup4
duckduckgo-search
```

Install dependencies:

```bash
pip install playwright requests beautifulsoup4 duckduckgo-search
playwright install chromium
```

---

## Usage

```bash
python npp_scraper.py
```

No arguments required. Output is written to a timestamped CSV in the working directory:

```
privacy_contacts_20260504_110809.csv
```

To change the number of providers collected, edit the constants near the top of the file:

```python
TARGET_COUNT = 100   # How many providers to collect
MAX_PAGES    = 10    # Maximum portal pages to paginate through
```

---

## Output Format

Each row in the CSV corresponds to one provider. Fields:

| Field | Description |
|---|---|
| `provider_name` | Name as it appears on the HHS portal |
| `website` | Base URL of the discovered official site |
| `emails` | Semicolon-separated list of email addresses found |
| `phones` | Semicolon-separated list of phone numbers found |
| `source_url` | The specific page where contact info was located |
| `context_snippet` | Up to 300 characters of surrounding text for verification |
| `found_via` | `site crawl`, `web search`, or `not found` |

Providers for which no contact information could be located still appear in the CSV with `found_via = "not found"` and blank contact fields, so the output roster always covers every input provider.

---

## Example Output

**Successful finds:**

| provider_name | website | emails | found_via |
|---|---|---|---|
| Springfield Hospital | https://springfieldhospital.org | achaffee@springfield-hospital.org | web search |
| Option Care Health, Inc. | https://optioncarehealth.com | OC-Privacy@optioncare.com | web search |
| Woodfords Family Services | https://www.woodfords.org | shayward@woodfords.org | web search |

**Not found:**

| provider_name | website | emails | found_via |
|---|---|---|---|
| Hospital Caribbean Medical Center | https://caribbeanmedicalcenter.com | | not found |
| Interventional Pain Center, PLLC | https://ipcpaincenter.com | | not found |

---

## Performance

The pipeline is sequential and rate-conscious. Each provider requires multiple DuckDuckGo queries and HTTP fetches, so expect roughly **30–90 seconds per provider** depending on site responsiveness. A full 100-provider run typically takes **1–3 hours**.

If speed is a priority, the per-provider block in `main()` is a natural unit to parallelize with `concurrent.futures.ThreadPoolExecutor`. Add randomized delays between DDG calls to avoid throttling.

---

## Known Limitations

**Website misidentification.** The DuckDuckGo site-discovery step occasionally returns an aggregator, news article, or third-party vendor instead of the provider's own domain. For example, a HIPAA email security vendor may rank highly for a small clinic's name. Always verify `source_url` and `context_snippet` before using contact data for outreach.

**Email false positives.** The regex extracts any email address found near privacy-related keywords. This can include webmaster addresses, form submission endpoints, or contacts belonging to third-party services embedded on the page.

**Dynamic pages.** The contact-extraction step uses plain HTTP requests and BeautifulSoup. Pages that load content via JavaScript will not be fully parsed. If a provider's privacy notice is rendered client-side, the crawl step may return no results even when contact info exists.

**DDG rate limits.** DuckDuckGo may throttle or temporarily block requests during long runs. The tool catches and logs search errors, skips to the next query, and continues rather than failing hard.

---

## Adapting to Other Use Cases

**Different input source.** The HHS portal scraper (`get_healthcare_providers()`) is fully decoupled from the contact-finding pipeline. Replace it with any function that returns a plain Python list of organization name strings, and the rest of the pipeline runs unchanged — useful if your providers come from a spreadsheet, a database, or a different regulatory portal.

**Different privacy keyword patterns.** The `context_patterns` list in `extract_privacy_contact()` targets HIPAA-specific language. For other regulatory contexts (GDPR data controllers, state AG consumer contacts, etc.), swap in the terminology relevant to your domain.

**Different URL paths.** The `PRIVACY_PATHS` list covers common conventions for US healthcare sites. Extend or replace it to match the URL structures common in your target sector.

**Domain blocklist.** The `BAD_DOMAINS` list filters out aggregators and social platforms that frequently rank highly but are not official sources. Add domains you observe polluting your results, or remove entries that are actually authoritative for your use case.

---

## License

This tool is intended for research and compliance use. Respect the terms of service of any website you crawl. Contact data collected should be used in accordance with applicable law.
