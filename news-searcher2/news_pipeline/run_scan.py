"""
Main entry point. Runs all enabled scanners and stores results in SQLite.

Usage:
    python run_scan.py
"""

from __future__ import annotations
import logging

from scanners.rss_scanner import RSSScanner
from storage.db import init_db, get_connection, insert_articles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_scan")

# Add new scanner instances here as new modules are built.
# Each one just needs a .fetch() method that returns list[Article].
SCANNERS = [
    RSSScanner(),
]


def main():
    init_db()
    conn = get_connection()

    total_summary = {"inserted": 0, "duplicate_url": 0, "duplicate_content": 0}

    for scanner in SCANNERS:
        logger.info("Running scanner: %s", scanner.name)
        try:
            articles = scanner.fetch()
        except Exception as e:
            logger.error("Scanner %s failed entirely: %s", scanner.name, e)
            continue

        logger.info("Scanner %s found %d candidate articles", scanner.name, len(articles))
        summary = insert_articles(conn, articles)
        logger.info("Scanner %s results: %s", scanner.name, summary)

        for key in total_summary:
            total_summary[key] += summary[key]

    conn.close()
    logger.info("Done. Totals: %s", total_summary)


if __name__ == "__main__":
    main()
