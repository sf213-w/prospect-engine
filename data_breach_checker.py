#!/usr/bin/env python3
"""
Data Breach News Scanner
Run weekly to collect and report on recent data breach news.
Usage: python data_breach_scanner.py
Requires: pip install requests beautifulsoup4 feedparser
"""

import feedparser
import requests
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
LOOKBACK_DAYS = 7          # How far back to search
OUTPUT_DIR = Path("breach_reports")  # Where to save reports
SAVE_REPORT = True         # Save a JSON + TXT report each run

# RSS/Atom feeds known for data breach coverage
RSS_FEEDS = [
    ("Krebs on Security",        "https://krebsonsecurity.com/feed/"),
    ("Dark Reading",             "https://www.darkreading.com/rss.xml"),
    ("BleepingComputer Security","https://www.bleepingcomputer.com/feed/"),
    ("The Hacker News",          "https://feeds.feedburner.com/TheHackersNews"),
    ("SecurityWeek",             "https://feeds.feedburner.com/Securityweek"),
    ("Infosecurity Magazine",    "https://www.infosecurity-magazine.com/rss/news/"),
    ("SC Magazine",              "https://www.scmagazine.com/feed"),
    ("DataBreaches.net",         "https://www.databreaches.net/feed/"),
    ("Have I Been Pwned Blog",   "https://feeds.feedburner.com/HaveIBeenPwnedLatestBreaches"),
]

# Keywords to match (case-insensitive); any match = include the article
KEYWORDS = [
    "data breach", "databreach", "data leak", "data exposure",
    "hack", "hacked", "cyberattack", "cyber attack",
    "ransomware", "stolen data", "leaked data",
    "unauthorized access", "security incident",
    "personal information exposed", "records exposed",
    "credential stuffing", "phishing attack",
]

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def parse_entry_date(entry) -> datetime | None:
    """Return a timezone-aware datetime from a feedparser entry, or None."""
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def is_recent(dt: datetime | None, cutoff: datetime) -> bool:
    return dt is not None and dt >= cutoff


def matches_keywords(text: str) -> bool:
    low = text.lower()
    return any(kw in low for kw in KEYWORDS)


def clean_html(raw: str) -> str:
    """Strip HTML tags for plain-text summary."""
    return re.sub(r"<[^>]+>", "", raw).strip()


def scan_feeds(cutoff: datetime) -> list[dict]:
    """Fetch all RSS feeds and return matching articles."""
    results = []
    for source_name, url in RSS_FEEDS:
        print(f"  Checking {source_name} ...", end=" ", flush=True)
        try:
            feed = feedparser.parse(url)
            matched = 0
            for entry in feed.entries:
                pub_date = parse_entry_date(entry)
                if not is_recent(pub_date, cutoff):
                    continue
                title   = entry.get("title", "")
                summary = clean_html(entry.get("summary", entry.get("description", "")))
                link    = entry.get("link", "")
                if matches_keywords(title + " " + summary):
                    results.append({
                        "source":    source_name,
                        "title":     title,
                        "summary":   summary[:400] + ("…" if len(summary) > 400 else ""),
                        "url":       link,
                        "published": pub_date.strftime("%Y-%m-%d %H:%M UTC") if pub_date else "Unknown",
                        "published_dt": pub_date,
                    })
                    matched += 1
            print(f"{matched} match(es)")
        except Exception as e:
            print(f"ERROR — {e}")
    return results


def deduplicate(articles: list[dict]) -> list[dict]:
    """Remove near-duplicate titles (same first 60 chars)."""
    seen, out = set(), []
    for a in articles:
        key = a["title"][:60].lower().strip()
        if key not in seen:
            seen.add(key)
            out.append(a)
    return out


def sort_articles(articles: list[dict]) -> list[dict]:
    return sorted(
        articles,
        key=lambda a: a.get("published_dt") or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )


def print_report(articles: list[dict], cutoff: datetime) -> None:
    now = datetime.now(timezone.utc)
    print("\n" + "═" * 65)
    print(f"  DATA BREACH NEWS REPORT")
    print(f"  Generated : {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Covering  : Last {LOOKBACK_DAYS} days ({cutoff.strftime('%Y-%m-%d')} → today)")
    print(f"  Articles  : {len(articles)} matched")
    print("═" * 65)

    if not articles:
        print("\n  No matching articles found in the configured feeds.\n")
        return

    for i, a in enumerate(articles, 1):
        print(f"\n[{i}] {a['title']}")
        print(f"    Source    : {a['source']}")
        print(f"    Published : {a['published']}")
        print(f"    URL       : {a['url']}")
        if a["summary"]:
            print(f"    Summary   : {a['summary']}")
    print("\n" + "═" * 65 + "\n")


def save_report(articles: list[dict], cutoff: datetime) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    # JSON
    json_path = OUTPUT_DIR / f"breaches_{stamp}.json"
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "lookback_days": LOOKBACK_DAYS,
        "article_count": len(articles),
        "articles": [
            {k: v for k, v in a.items() if k != "published_dt"}
            for a in articles
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    # Plain text
    txt_path = OUTPUT_DIR / f"breaches_{stamp}.txt"
    lines = [
        f"DATA BREACH REPORT — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        f"Lookback: {LOOKBACK_DAYS} days | Articles: {len(articles)}",
        "=" * 65,
    ]
    for i, a in enumerate(articles, 1):
        lines += [
            f"\n[{i}] {a['title']}",
            f"  Source    : {a['source']}",
            f"  Published : {a['published']}",
            f"  URL       : {a['url']}",
            f"  Summary   : {a['summary']}",
        ]
    txt_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"  Reports saved to:")
    print(f"    {json_path}")
    print(f"    {txt_path}")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    print(f"\nData Breach Scanner — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Scanning {len(RSS_FEEDS)} feeds for the past {LOOKBACK_DAYS} days …\n")

    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    articles = scan_feeds(cutoff)
    articles = deduplicate(articles)
    articles = sort_articles(articles)

    print_report(articles, cutoff)

    if SAVE_REPORT:
        save_report(articles, cutoff)


if __name__ == "__main__":
    main()