# npp_scraper.py

import time
import re
import csv
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from ddgs import DDGS
from urllib.parse import urlparse
from datetime import datetime

URL = "https://ocrportal.hhs.gov/ocr/breach/breach_report_hip.jsf"

TARGET_COUNT = 100
MAX_PAGES = 10

CSV_FILE = f"privacy_contacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
CSV_FIELDS = [
    "provider_name",
    "website",
    "emails",
    "phones",
    "source_url",
    "context_snippet",
    "found_via",
    "date_scraped",
]


# -----------------------------
# CSV WRITER
# -----------------------------
def init_csv():
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
    print(f"📄 CSV initialized: {CSV_FILE}")


def write_csv_row(row: dict):
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writerow(row)


def write_not_found(provider_name, website=""):
    write_csv_row({
        "provider_name": provider_name,
        "website": website,
        "emails": "",
        "phones": "",
        "source_url": "",
        "context_snippet": "",
        "found_via": "not found",
        "date_scraped": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


# -----------------------------
# WAIT FOR TABLE DATA
# -----------------------------
def wait_for_table_data(page):
    page.wait_for_selector("tbody tr")
    for _ in range(10):
        rows = page.query_selector_all("tbody tr")
        if rows:
            text = rows[0].inner_text().strip()
            if text:
                return True
        time.sleep(1)
    return False


# -----------------------------
# PARSE ROW SAFELY
# -----------------------------
def parse_row(row):
    cols = row.query_selector_all("td")
    values = [c.inner_text().strip() for c in cols]

    if len(values) < 3:
        return None, None

    name = None
    entity_type = None

    for v in values:
        if "Healthcare Provider" in v or "Health Plan" in v:
            entity_type = v
        elif len(v) > 3 and not v.isupper():
            if not name:
                name = v

    return name, entity_type


# -----------------------------
# EXTRACT PROVIDERS
# -----------------------------
def extract_providers(page, collected):
    rows = page.query_selector_all("tbody tr")
    for row in rows:
        name, entity_type = parse_row(row)
        if not name or not entity_type:
            continue
        print(f"  DEBUG: {name} | {entity_type}")
        if "Healthcare Provider" in entity_type:
            if name not in collected:
                collected.append(name)
        if len(collected) >= TARGET_COUNT:
            return True
    return False


# -----------------------------
# PAGINATION
# -----------------------------
def go_to_next_page(page):
    try:
        next_button = page.query_selector('a[aria-label="Next"], a:has-text("Next")')
        if not next_button:
            return False
        class_attr = next_button.get_attribute("class") or ""
        if "ui-state-disabled" in class_attr:
            return False
        next_button.click()
        page.wait_for_timeout(2000)
        wait_for_table_data(page)
        return True
    except:
        return False


# -----------------------------
# SCRAPE HHS
# -----------------------------
def get_healthcare_providers():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Loading HHS portal...")
        page.goto(URL, timeout=60000)

        if not wait_for_table_data(page):
            print("Retrying...")
            page.reload()
            wait_for_table_data(page)

        collected = []
        page_num = 1

        while page_num <= MAX_PAGES:
            print(f"\n--- PAGE {page_num} ---")
            done = extract_providers(page, collected)
            if done:
                break
            if not go_to_next_page(page):
                print("No more pages.")
                break
            page_num += 1

        browser.close()
        return collected


# -----------------------------
# DOMAIN FILTER
# -----------------------------
BAD_DOMAINS = [
    "linkedin.com", "facebook.com", "twitter.com", "instagram.com",
    "youtube.com", "healthgrades.com", "mapquest.com", "popupportal.com",
    "wikipedia.org", "yelp.com", "claimdepot.com", "databreach",
    "classaction.org", "topclassactions.com", "hipaajournal.com",
    "hhs.gov", "cms.gov", "bbb.org", "glassdoor.com", "indeed.com",
    "doximity.com", "vitals.com", "webmd.com", "zocdoc.com",
]

def is_valid_domain(url):
    return not any(bad in url for bad in BAD_DOMAINS)


# -----------------------------
# GET BASE URL (scheme + domain only)
# -----------------------------
def get_base_url(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


# -----------------------------
# FIND OFFICIAL WEBSITE
# -----------------------------
def find_official_site(company):
    queries = [
        f'"{company}" official site privacy officer contact',
        f'"{company}" hospital clinic official website',
        f"{company} healthcare privacy HIPAA contact",
    ]

    for query in queries:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=8))

            for r in results:
                url = r.get("href") or r.get("url")
                if not url:
                    continue
                if not is_valid_domain(url):
                    continue
                base = get_base_url(url)
                if base:
                    return base

        except Exception as e:
            print(f"  Search error: {e}")
            continue

    return None


# -----------------------------
# EXTRACT EMAILS FROM TEXT
# -----------------------------
def extract_emails(text):
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    return list(set(re.findall(pattern, text)))


# -----------------------------
# EXTRACT PRIVACY OFFICER INFO
# -----------------------------
def extract_privacy_contact(text, source_url):
    results = []

    context_patterns = [
        r".{0,300}privacy officer.{0,300}",
        r".{0,300}compliance officer.{0,300}",
        r".{0,300}HIPAA.{0,300}",
        r".{0,300}data protection officer.{0,300}",
        r".{0,300}chief privacy.{0,300}",
    ]

    for pattern in context_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            snippet = match.group()
            emails = extract_emails(snippet)
            phones = re.findall(r"\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}", snippet)

            results.append({
                "snippet": snippet[:300].strip(),
                "emails": emails,
                "phones": phones,
                "source": source_url,
            })

    return results


# -----------------------------
# FETCH PAGE TEXT
# -----------------------------
def fetch_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(" ", strip=True)
    except:
        return None


# -----------------------------
# SEARCH INSIDE SITE FOR PRIVACY PAGE
# -----------------------------
PRIVACY_PATHS = [
    "/privacy",
    "/privacy-policy",
    "/privacy-notice",
    "/hipaa",
    "/hipaa-notice",
    "/compliance",
    "/contact",
    "/contact-us",
    "/about/privacy",
    "/about/contact",
    "/patients/privacy",
    "/notices/privacy",
]

def find_privacy_contact(base_url):
    all_contacts = []

    for path in PRIVACY_PATHS:
        url = base_url.rstrip("/") + path
        print(f"  Checking: {url}")
        text = fetch_text(url)

        if not text:
            continue

        contacts = extract_privacy_contact(text, url)
        if contacts:
            all_contacts.extend(contacts)
            if any(c["emails"] for c in contacts):
                break

    return all_contacts


# -----------------------------
# SEARCH DDG FOR PRIVACY OFFICER EMAIL
# -----------------------------
def search_for_privacy_officer(company):
    queries = [
        f'"{company}" "privacy officer" email contact',
        f'"{company}" HIPAA privacy notice contact email',
    ]

    for query in queries:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))

            for r in results:
                url = r.get("href") or r.get("url")
                snippet_text = r.get("body", "")

                emails = extract_emails(snippet_text)
                if emails:
                    return emails, url

                if url and is_valid_domain(url):
                    text = fetch_text(url)
                    if text:
                        contacts = extract_privacy_contact(text, url)
                        for c in contacts:
                            if c["emails"]:
                                return c["emails"], url

        except Exception as e:
            print(f"  Search error: {e}")
            continue

    return [], None


# -----------------------------
# MAIN PIPELINE
# -----------------------------
def main():
    print("Starting full pipeline...\n")

    init_csv()

    providers = get_healthcare_providers()

    if not providers:
        print("❌ No providers found")
        return

    print(f"\n✅ {len(providers)} providers found:")
    for p in providers:
        print(" -", p)

    print("\n🔍 Finding privacy officer contacts...\n")

    for provider in providers:
        print(f"\n{'='*60}")
        print(f"  {provider}")
        print(f"{'='*60}")

        # Step 1: Find the official site
        site = find_official_site(provider)
        if not site:
            print("  ❌ No official site found")
            write_not_found(provider)
            continue

        print(f"  🌐 Website: {site}")

        found_anything = False
        scrape_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Step 2: Check known privacy-related paths on the site
        contacts = find_privacy_contact(site)

        for c in contacts:
            if c["emails"] or c["phones"]:
                found_anything = True
                print(f"\n  ✅ Contact found at: {c['source']}")
                if c["emails"]:
                    print(f"     📧 Emails: {', '.join(c['emails'])}")
                if c["phones"]:
                    print(f"     📞 Phones: {', '.join(c['phones'])}")
                print(f"     📝 Context: ...{c['snippet'][:200]}...")

                write_csv_row({
                    "provider_name": provider,
                    "website": site,
                    "emails": "; ".join(c["emails"]),
                    "phones": "; ".join(c["phones"]),
                    "source_url": c["source"],
                    "context_snippet": c["snippet"][:300],
                    "found_via": "site crawl",
                    "date_scraped": scrape_time,
                })

        # Step 3: If nothing found on-site, try a targeted web search
        if not found_anything:
            print(f"\n  🔎 Trying targeted web search for privacy officer...")
            emails, source = search_for_privacy_officer(provider)
            if emails:
                print(f"  ✅ Found via web search!")
                print(f"     📧 Emails: {', '.join(emails)}")
                print(f"     Source: {source}")

                write_csv_row({
                    "provider_name": provider,
                    "website": site,
                    "emails": "; ".join(emails),
                    "phones": "",
                    "source_url": source,
                    "context_snippet": "",
                    "found_via": "web search",
                    "date_scraped": scrape_time,
                })
            else:
                print(f"  ❌ No privacy officer contact found")
                write_not_found(provider, site)

    print(f"\n✅ Done. Results saved to: {CSV_FILE}")


if __name__ == "__main__":
    main()