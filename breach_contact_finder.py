#!/usr/bin/env python3
"""
Breach Contact Finder v2
Reads the latest breach scanner JSON report, extracts US company names,
finds their websites, and scrapes contact information for sales outreach.

Usage:
    python breach_contact_finder.py                      # uses latest report
    python breach_contact_finder.py path/to/report.json  # specific report

Requires:
    pip install requests beautifulsoup4
"""

import json
import re
import sys
import csv
import time
from pathlib import Path
from datetime import datetime
import urllib.parse

import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
BREACH_REPORTS_DIR = Path("breach_reports")
OUTPUT_DIR         = Path("breach_reports")
REQUEST_DELAY      = 2
REQUEST_TIMEOUT    = 12
MAX_PAGES_PER_SITE = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

SKIP_DOMAINS = [
    "linkedin", "twitter", "facebook", "wikipedia", "yelp",
    "bloomberg", "reuters", "techcrunch", "forbes", "crunchbase",
    "glassdoor", "indeed", "youtube", "instagram", "reddit",
    "bleepingcomputer", "darkreading", "securityweek", "krebsonsecurity",
    "thehackernews", "databreaches", "infosecurity-magazine", "scmagazine",
    "haveibeenpwned", "feedburner", "google", "bing", "yahoo", "duckduckgo",
    "sec.gov", "justice.gov", "cisa.gov", "bbb.org", "dnb.com", "zoominfo",
    "manta.com", "bizapedia", "opencorporates",
]

CONTACT_PAGE_PATHS = [
    "/contact", "/contact-us", "/contact_us", "/about/contact",
    "/company/contact", "/support", "/security", "/about", "/about-us",
]

# ──────────────────────────────────────────────
# STEP 1 — LOAD REPORT
# ──────────────────────────────────────────────

def find_latest_report():
    reports = sorted(BREACH_REPORTS_DIR.glob("breaches_*.json"), reverse=True)
    if not reports:
        print(f"ERROR: No breach reports found in {BREACH_REPORTS_DIR}/")
        print("       Run data_breach_scanner.py first.")
        sys.exit(1)
    return reports[0]


def load_report(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("articles", [])


# ──────────────────────────────────────────────
# STEP 2 — EXTRACT COMPANY NAMES
# ──────────────────────────────────────────────

REJECT_PATTERNS = [
    r"^\d",
    r"^(iran|russia|china|north korea|south africa|europe|ukraine)",
    r"^(ex-|former|retired)",
    r"(hacker|gang|group|actor|threat|campaign|operation|government|agency|director|senator|official)",
    r"^(how|what|why|when|the latest|new|update|report|analysis|inside|behind|meet)",
    r"^[a-z]",
]

KNOWN_COMPANIES = {
    "carecloud", "corewell health", "woodfords family services",
    "infinite campus", "checkmarx", "stryker", "citrix", "f5",
    "sound radix", "scuf gaming", "telnyx",
}

def is_likely_company(name):
    low = name.lower().strip()
    if low in KNOWN_COMPANIES:
        return True
    for pat in REJECT_PATTERNS:
        if re.search(pat, low):
            return False
    words = low.split()
    if len(words) == 0 or len(name) < 3 or len(words) > 5:
        return False
    return True


EXTRACT_PATTERNS = [
    r"^([A-Z][A-Za-z0-9\s&\.\-']{2,40}?)\s+(?:data breach|data leak|hack|hacked|ransomware|cyberattack|cyber attack|security breach|security incident|discloses|confirms|probing|suffers|reports breach|notif)",
    r"(?:breach|hack|attack|leak|incident)\s+(?:at|of|hits?|targets?|on)\s+([A-Z][A-Za-z0-9\s&\.\-']{2,40}?)(?:\s*[,\|\-]|$|\s+exposes|\s+affects|\s+impacts|\s+leaks)",
    r"^([A-Z][A-Za-z0-9\s&\.\-']{2,40}?)\s+(?:exposes?|leaks?|loses?|reveals?|discloses?)\s+(?:\d+[mk]?\s+)?(?:user|customer|patient|employee|student|records?|accounts?|data|information)",
    r"^([A-Z][A-Za-z0-9\s&\.\-']{2,40}?)\s+(?:notif|files|reports|discloses|confirms|warns|alerts)",
]

def extract_company_name(title):
    for pattern in EXTRACT_PATTERNS:
        m = re.search(pattern, title)
        if m:
            candidate = m.group(1).strip().rstrip(".,;:-")
            candidate = re.sub(r"^(The|A|An)\s+", "", candidate)
            if is_likely_company(candidate):
                return candidate
    return None


def extract_companies(articles):
    companies = {}
    for article in articles:
        title = article.get("title", "")
        name  = extract_company_name(title)
        if not name:
            continue
        key = name.lower().strip()
        if key not in companies:
            companies[key] = {
                "company_name":   name,
                "article_title":  title,
                "article_url":    article.get("url", ""),
                "article_source": article.get("source", ""),
                "published":      article.get("published", ""),
                "summary":        article.get("summary", "")[:200],
            }
    return list(companies.values())


# ──────────────────────────────────────────────
# STEP 3 — FIND COMPANY WEBSITE
# ──────────────────────────────────────────────

def duckduckgo_search(query):
    try:
        encoded = urllib.parse.urlencode({"q": query, "kl": "us-en"})
        url = f"https://html.duckduckgo.com/html/?{encoded}"
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        urls = []
        for a in soup.select("a.result__a"):
            href = a.get("href", "")
            if "uddg=" in href:
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                real = parsed.get("uddg", [""])[0]
                if real:
                    href = urllib.parse.unquote(real)
            if href.startswith("http"):
                urls.append(href)
        return urls
    except Exception as e:
        print(f"      Search error: {e}")
        return []


def find_company_website(company_name):
    # Try direct domain guess first
    slug = re.sub(r"[^a-z0-9]", "", company_name.lower())
    guesses = [
        f"https://www.{slug}.com",
        f"https://{slug}.com",
    ]
    for guess in guesses:
        try:
            resp = requests.get(guess, headers=HEADERS, timeout=6, allow_redirects=True)
            if resp.status_code == 200:
                return resp.url
        except Exception:
            pass

    time.sleep(REQUEST_DELAY)

    # Fall back to DuckDuckGo
    query = f'"{company_name}" official site contact'
    results = duckduckgo_search(query)
    for url in results:
        if any(skip in url.lower() for skip in SKIP_DOMAINS):
            continue
        parsed = urllib.parse.urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    return None


# ──────────────────────────────────────────────
# STEP 4 — SCRAPE CONTACT INFO
# ──────────────────────────────────────────────

EMAIL_RE   = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE   = re.compile(r"(\+?1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}")
ADDRESS_RE = re.compile(
    r"\d{1,5}\s[\w\s]{3,40},\s*[\w\s]{2,30},\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?",
    re.IGNORECASE
)

JUNK_EMAIL_FRAGMENTS = [
    "example", "noreply", "no-reply", "test@", "user@",
    "email@", "name@", "domain", "yourname", "sentry",
    "wixpress", "squarespace",
]

def is_junk_email(email):
    low = email.lower()
    if low.endswith((".png", ".jpg", ".gif", ".svg", ".css", ".js")):
        return True
    return any(j in low for j in JUNK_EMAIL_FRAGMENTS)

def classify_email(email):
    low = email.lower()
    if any(k in low for k in ["security", "abuse", "cert", "csirt", "vuln", "psirt"]):
        return "security"
    return "general"


def fetch_page(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, "html.parser")
    except Exception:
        pass
    return None


def scrape_contact_info(base_url):
    base = base_url.rstrip("/")
    emails_general  = set()
    emails_security = set()
    phones          = set()
    addresses       = set()

    pages   = [base] + [base + p for p in CONTACT_PAGE_PATHS[:MAX_PAGES_PER_SITE]]
    checked = 0

    for page_url in pages:
        if checked > MAX_PAGES_PER_SITE:
            break
        soup = fetch_page(page_url)
        if not soup:
            continue

        text = soup.get_text(separator=" ")

        for em in EMAIL_RE.findall(text):
            if not is_junk_email(em):
                if classify_email(em) == "security":
                    emails_security.add(em.lower())
                else:
                    emails_general.add(em.lower())

        for ph in PHONE_RE.findall(text):
            digits = re.sub(r"\D", "", ph)
            if len(digits) in (10, 11):
                phones.add(ph.strip())

        for addr in ADDRESS_RE.findall(text):
            addresses.add(addr.strip())

        checked += 1
        time.sleep(REQUEST_DELAY)

    return {
        "emails_general":  ", ".join(sorted(emails_general))[:300],
        "emails_security": ", ".join(sorted(emails_security))[:300],
        "phones":          ", ".join(sorted(phones))[:200],
        "addresses":       " | ".join(sorted(addresses))[:300],
    }


# ──────────────────────────────────────────────
# STEP 5 — SAVE RESULTS
# ──────────────────────────────────────────────

def save_results(results):
    OUTPUT_DIR.mkdir(exist_ok=True)
    stamp    = datetime.now().strftime("%Y%m%d_%H%M")
    csv_path = OUTPUT_DIR / f"breach_contacts_{stamp}.csv"

    fieldnames = [
        "company_name", "website", "emails_general", "emails_security",
        "phones", "addresses", "article_title", "article_source",
        "published", "article_url", "summary",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    return csv_path


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        report_path = Path(sys.argv[1])
    else:
        report_path = find_latest_report()

    print(f"\nBreach Contact Finder v2")
    print(f"Reading: {report_path}\n")

    articles  = load_report(report_path)
    print(f"  Loaded {len(articles)} articles")

    companies = extract_companies(articles)
    print(f"  Extracted {len(companies)} company names:\n")
    for c in companies:
        print(f"    - {c['company_name']}")
    print()

    if not companies:
        print("  No company names found. Exiting.")
        sys.exit(0)

    results = []
    for i, company in enumerate(companies, 1):
        name = company["company_name"]
        print(f"[{i}/{len(companies)}] {name}")

        print(f"    Searching for website...", end=" ", flush=True)
        website = find_company_website(name)

        if website:
            print(f"found: {website}")
            print(f"    Scraping contact pages...")
            contact = scrape_contact_info(website)
            if contact["emails_general"]:
                print(f"    Email    : {contact['emails_general'][:80]}")
            if contact["emails_security"]:
                print(f"    Security : {contact['emails_security'][:80]}")
            if contact["phones"]:
                print(f"    Phone    : {contact['phones'][:60]}")
            if contact["addresses"]:
                print(f"    Address  : {contact['addresses'][:80]}")
            if not any(contact.values()):
                print(f"    No contact info found on site")
        else:
            print("not found")
            contact = {
                "emails_general": "", "emails_security": "",
                "phones": "", "addresses": "",
            }

        results.append({**company, "website": website or "", **contact})
        time.sleep(REQUEST_DELAY)

    csv_path = save_results(results)
    found = sum(1 for r in results if r.get("website"))
    print(f"\n  Done. {found}/{len(companies)} companies found.")
    print(f"  Saved to: {csv_path}\n")


if __name__ == "__main__":
    main()