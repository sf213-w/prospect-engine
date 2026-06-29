"""
SQLite storage layer for the news pipeline.

Handles schema creation and inserting articles with two layers of dedup:
  1. Exact: UNIQUE constraint on url
  2. Near-duplicate: a hash of normalized article text, so the same wire
     story re-published on multiple sites doesn't get stored twice.
"""

from __future__ import annotations
import hashlib
import re
import sqlite3
from pathlib import Path

from scanners.base import Article

DB_PATH = Path(__file__).parent / "pipeline.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    text TEXT,
    published_at TEXT,
    source_name TEXT,
    source_type TEXT,
    fetched_at TEXT,
    content_hash TEXT,
    status TEXT DEFAULT 'new'
);

CREATE INDEX IF NOT EXISTS idx_articles_content_hash ON articles(content_hash);
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _normalize_text_for_hash(text: str) -> str:
    """Lowercase and collapse whitespace so trivial formatting differences
    (extra spaces, line breaks) don't defeat the dedup check."""
    return re.sub(r"\s+", " ", text.strip().lower())


def content_hash(text: str) -> str:
    normalized = _normalize_text_for_hash(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def insert_article(conn: sqlite3.Connection, article: Article) -> tuple[bool, str]:
    """
    Insert an article if it's new. Returns (inserted, reason).
    reason is one of: "inserted", "duplicate_url", "duplicate_content"
    """
    chash = content_hash(article.text) if article.text else None

    cur = conn.execute("SELECT 1 FROM articles WHERE url = ?", (article.url,))
    if cur.fetchone():
        return False, "duplicate_url"

    if chash:
        cur = conn.execute(
            "SELECT 1 FROM articles WHERE content_hash = ?", (chash,)
        )
        if cur.fetchone():
            return False, "duplicate_content"

    conn.execute(
        """
        INSERT INTO articles
            (url, title, text, published_at, source_name, source_type,
             fetched_at, content_hash, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')
        """,
        (
            article.url,
            article.title,
            article.text,
            article.published_at,
            article.source_name,
            article.source_type,
            article.fetched_at,
            chash,
        ),
    )
    conn.commit()
    return True, "inserted"


def insert_articles(conn: sqlite3.Connection, articles: list[Article]) -> dict:
    """Bulk insert with a summary count, used by the scanner runner."""
    summary = {"inserted": 0, "duplicate_url": 0, "duplicate_content": 0}
    for article in articles:
        _, reason = insert_article(conn, article)
        summary[reason] += 1
    return summary
