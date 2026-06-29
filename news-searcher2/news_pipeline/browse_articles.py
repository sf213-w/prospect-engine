"""
Browse articles stored in pipeline.db -- no sqlite3 CLI tool required.

Usage examples:
    python browse_articles.py
        -> lists all articles (id, source, title), most recent first

    python browse_articles.py --source "Krebs on Security"
        -> only articles from that source

    python browse_articles.py --search hipaa
        -> only articles whose title or text contains "hipaa" (case-insensitive)

    python browse_articles.py --id 5
        -> show full details (including full text) for article id 5

    python browse_articles.py --counts
        -> show how many articles came from each source
"""

from __future__ import annotations
import argparse
import sqlite3
import textwrap
from pathlib import Path

DB_PATH = Path(__file__).parent / "storage" / "pipeline.db"


def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise SystemExit(
            f"No database found at {DB_PATH}. Run 'python run_scan.py' first."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def list_articles(conn: sqlite3.Connection, source: str | None, search: str | None):
    query = "SELECT id, title, source_name, published_at, url FROM articles"
    conditions = []
    params = []

    if source:
        conditions.append("source_name LIKE ?")
        params.append(f"%{source}%")
    if search:
        conditions.append("(title LIKE ? OR text LIKE ?)")
        params.append(f"%{search}%")
        params.append(f"%{search}%")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY fetched_at DESC"

    rows = conn.execute(query, params).fetchall()

    if not rows:
        print("No articles matched.")
        return

    print(f"{len(rows)} article(s):\n")
    for row in rows:
        title = textwrap.shorten(row["title"] or "(no title)", width=70, placeholder="...")
        print(f"[{row['id']:>4}] {row['source_name']:<22} {title}")
    print(f"\nTip: use --id <number> to read the full text of one article.")


def show_article(conn: sqlite3.Connection, article_id: int):
    row = conn.execute(
        "SELECT * FROM articles WHERE id = ?", (article_id,)
    ).fetchone()

    if not row:
        print(f"No article with id {article_id}.")
        return

    print("=" * 80)
    print(f"Title:       {row['title']}")
    print(f"Source:      {row['source_name']} ({row['source_type']})")
    print(f"URL:         {row['url']}")
    print(f"Published:   {row['published_at']}")
    print(f"Fetched:     {row['fetched_at']}")
    print(f"Status:      {row['status']}")
    print("=" * 80)
    print()
    print(row["text"])


def show_counts(conn: sqlite3.Connection):
    rows = conn.execute(
        "SELECT source_name, COUNT(*) as count FROM articles GROUP BY source_name ORDER BY count DESC"
    ).fetchall()

    total = sum(r["count"] for r in rows)
    print(f"Total articles: {total}\n")
    for row in rows:
        print(f"  {row['source_name']:<25} {row['count']}")


def main():
    parser = argparse.ArgumentParser(description="Browse articles in pipeline.db")
    parser.add_argument("--source", help="Filter by source name (partial match OK)")
    parser.add_argument("--search", help="Filter by keyword in title or text")
    parser.add_argument("--id", type=int, help="Show full details for one article by id")
    parser.add_argument("--counts", action="store_true", help="Show article counts per source")
    args = parser.parse_args()

    conn = get_connection()
    try:
        if args.id is not None:
            show_article(conn, args.id)
        elif args.counts:
            show_counts(conn)
        else:
            list_articles(conn, args.source, args.search)
    finally:
        conn.close()


if __name__ == "__main__":
    main()