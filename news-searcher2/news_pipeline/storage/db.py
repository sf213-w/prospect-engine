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

CREATE TABLE IF NOT EXISTS tags (
    article_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    FOREIGN KEY(article_id) REFERENCES articles(id),
    UNIQUE(article_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
CREATE INDEX IF NOT EXISTS idx_tags_article_id ON tags(article_id);

CREATE TABLE IF NOT EXISTS story_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT,
    article_ids TEXT,      -- JSON list of source article ids used
    parameters TEXT,       -- JSON: topic, title, length, tone, model, etc.
    output_text TEXT
);
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    """
    Create any tables/indexes that don't exist yet, and migrate older
    articles tables that predate the content_hash/status columns.
    """
    conn = get_connection(db_path)
    try:
        _migrate_articles_table(conn)

        for statement in SCHEMA.strip().split(";"):
            statement = statement.strip()
            if not statement:
                continue
            try:
                conn.execute(statement)
            except sqlite3.OperationalError as e:
                print(f"Warning: skipping schema statement due to: {e}\n  {statement[:80]}...")
        conn.commit()
    finally:
        conn.close()


def _migrate_articles_table(conn: sqlite3.Connection) -> None:
    """Add columns to an existing articles table if an older version of
    this database predates them. Safe to call even if articles doesn't
    exist yet (the check just finds no columns and does nothing)."""
    existing_cols = {
        row[1] for row in conn.execute("PRAGMA table_info(articles)").fetchall()
    }
    if not existing_cols:
        return  # table doesn't exist yet; CREATE TABLE in SCHEMA will make it fresh

    if "content_hash" not in existing_cols:
        conn.execute("ALTER TABLE articles ADD COLUMN content_hash TEXT")
        print("Migrated: added content_hash column to articles")

    if "status" not in existing_cols:
        conn.execute("ALTER TABLE articles ADD COLUMN status TEXT DEFAULT 'new'")
        print("Migrated: added status column to articles")

    conn.commit()


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


def get_uncategorized_articles(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Articles that haven't been run through the categorizer yet."""
    return conn.execute(
        "SELECT id, title, text FROM articles WHERE status = 'new'"
    ).fetchall()


def set_article_tags(conn: sqlite3.Connection, article_id: int, tags: list[str]) -> None:
    """Replace this article's tags with the given list, and mark it
    categorized. Safe to re-run: clears old tags first so re-categorizing
    after a rule change doesn't leave stale tags behind."""
    conn.execute("DELETE FROM tags WHERE article_id = ?", (article_id,))
    for tag in tags:
        conn.execute(
            "INSERT OR IGNORE INTO tags (article_id, tag) VALUES (?, ?)",
            (article_id, tag),
        )
    new_status = "categorized" if tags else "categorized_no_match"
    conn.execute(
        "UPDATE articles SET status = ? WHERE id = ?", (new_status, article_id)
    )
    conn.commit()


def get_articles_by_tag(conn: sqlite3.Connection, tag: str) -> list[sqlite3.Row]:
    """All articles carrying a given tag, most recent first."""
    return conn.execute(
        """
        SELECT a.* FROM articles a
        JOIN tags t ON a.id = t.article_id
        WHERE t.tag = ?
        ORDER BY a.fetched_at DESC
        """,
        (tag,),
    ).fetchall()


def get_all_tags_with_counts(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Every tag currently in use and how many articles carry it."""
    return conn.execute(
        """
        SELECT tag, COUNT(*) as count FROM tags
        GROUP BY tag ORDER BY count DESC
        """
    ).fetchall()


def get_articles_by_ids(conn: sqlite3.Connection, article_ids: list[int]) -> list[sqlite3.Row]:
    """Fetch specific articles by id, preserving no particular order
    (caller can re-sort if needed). Skips ids that don't exist rather
    than raising, so a typo in one id doesn't kill the whole selection."""
    if not article_ids:
        return []
    placeholders = ",".join("?" for _ in article_ids)
    return conn.execute(
        f"SELECT * FROM articles WHERE id IN ({placeholders})", article_ids
    ).fetchall()


def save_story_run(
    conn: sqlite3.Connection,
    article_ids: list[int],
    parameters: dict,
    output_text: str,
) -> int:
    """Record a generated story and the inputs that produced it. Returns
    the new story_run id."""
    import json
    from datetime import datetime, timezone

    cur = conn.execute(
        """
        INSERT INTO story_runs (created_at, article_ids, parameters, output_text)
        VALUES (?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            json.dumps(article_ids),
            json.dumps(parameters),
            output_text,
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_story_run(conn: sqlite3.Connection, story_run_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM story_runs WHERE id = ?", (story_run_id,)
    ).fetchone()


def list_story_runs(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT id, created_at, article_ids, parameters FROM story_runs ORDER BY created_at DESC"
    ).fetchall()
