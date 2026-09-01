"""
RSS scanner module.

Reads a list of feed URLs from config/feeds.yaml, pulls each feed's
entries, and for each entry fetches the full article page and extracts
clean text with trafilatura (RSS entries usually only give a summary,
not the full article body).

Usage:
    scanner = RSSScanner()
    articles = scanner.fetch()
"""

from __future__ import annotations
import logging
from pathlib import Path

import feedparser
import requests
import trafilatura
import yaml

from scanners.base import Article

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "feeds.yaml"


class RSSScanner:
    name = "rss"

    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH, timeout: int = 15):
        self.config_path = config_path
        self.timeout = timeout
        self.feeds = self._load_feeds()

    def _load_feeds(self) -> list[dict]:
        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)
        return config.get("feeds", [])

    def fetch(self) -> list[Article]:
        articles: list[Article] = []
        for feed in self.feeds:
            feed_name = feed["name"]
            feed_url = feed["url"]
            try:
                entries = self._fetch_feed_entries(feed_url)
            except Exception as e:
                logger.warning("Failed to read feed %s (%s): %s", feed_name, feed_url, e)
                continue

            for entry_url, entry_title, entry_published in entries:
                article = self._build_article(
                    entry_url, entry_title, entry_published, feed_name
                )
                if article:
                    articles.append(article)

        return articles

    def _fetch_feed_entries(self, feed_url: str) -> list[tuple[str, str, str | None]]:
        # Fetch via requests (uses certifi's CA bundle) rather than letting
        # feedparser open the URL itself -- on Windows, feedparser/urllib
        # falls back to the OS certificate store, which can contain a
        # malformed root CA and break TLS verification for every feed.
        response = requests.get(feed_url, timeout=self.timeout)
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        if parsed.bozo and not parsed.entries:
            # bozo=True with no entries usually means the feed didn't parse at all
            raise ValueError(f"Could not parse feed: {parsed.bozo_exception}")

        results = []
        for entry in parsed.entries:
            url = entry.get("link")
            title = entry.get("title", "")
            published = entry.get("published", None) or entry.get("updated", None)
            if url:
                results.append((url, title, published))
        return results

    def _build_article(
        self, url: str, title: str, published: str | None, source_name: str
    ) -> Article | None:
        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                logger.warning("Could not download %s", url)
                return None

            text = trafilatura.extract(downloaded)
            if not text or len(text.strip()) < 100:
                # Too short to be a real article body -- skip rather than
                # store junk (paywalls, redirects, etc. often land here)
                logger.info("Skipping %s: extracted text too short", url)
                return None

        except Exception as e:
            logger.warning("Failed to extract article %s: %s", url, e)
            return None

        return Article(
            url=url,
            title=title,
            text=text,
            source_name=source_name,
            source_type="rss",
            published_at=published,
        )
