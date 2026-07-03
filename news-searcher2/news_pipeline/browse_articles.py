"""
Browse articles stored in pipeline.db -- no sqlite3 CLI tool required.

Usage examples:
    python browse_articles.py
        -> lists all articles (id, source, title, tags), most recent first

    python browse_articles.py --source "Krebs on Security"
        -> only articles from that source

    python browse_articles.py --search hipaa
        -> only articles whose title or text contains "hipaa" (case-insensitive)

    python browse_articles.py --tag ransomware
        -> only articles tagged "ransomware" (run categorize_articles.py first)

    python browse_articles.py --id 5
        -> show full details (including full text and tags) for article id 5

    python browse_articles.py --counts
        -> show how many articles came from each source

    python browse_articles.py --tags
        -> show every tag currently in use and how many articles have it
"""

from __future__ import annotations
import argparse
import sqlite3
import textwrap

from storage.db import DB_PATH


def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise SystemExit(
            f"No database found at {DB_PATH}. Run 'python run_scan.py' first."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _tags_for_article(conn: sqlite3.Connection, article_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT tag FROM tags WHERE article_id = ? ORDER BY tag", (article_id,)
    ).fetchall()
    return [r["tag"] for r in rows]


def list_articles(
    conn: sqlite3.Connection,
    source: str | None,
    search: str | None,
    tag: str | None,
):
    if tag:
        # Filtering by tag requires a join, so build that query separately
        query = """
            SELECT a.id, a.title, a.source_name, a.published_at, a.url
            FROM articles a
            JOIN tags t ON a.id = t.article_id
            WHERE t.tag = ?
        """
        params: list = [tag]
        if source:
            query += " AND a.source_name LIKE ?"
            params.append(f"%{source}%")
        if search:
            query += " AND (a.title LIKE ? OR a.text LIKE ?)"
            params.append(f"%{search}%")
            params.append(f"%{search}%")
        query += " ORDER BY a.fetched_at DESC"
    else:
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
        title = textwrap.shorten(row["title"] or "(no title)", width=60, placeholder="...")
        article_tags = _tags_for_article(conn, row["id"])
        tag_str = f"  [{', '.join(article_tags)}]" if article_tags else ""
        print(f"[{row['id']:>4}] {row['source_name']:<22} {title}{tag_str}")
    print(f"\nTip: use --id <number> to read the full text of one article.")


def show_article(conn: sqlite3.Connection, article_id: int):
    row = conn.execute(
        "SELECT * FROM articles WHERE id = ?", (article_id,)
    ).fetchone()

    if not row:
        print(f"No article with id {article_id}.")
        return

    article_tags = _tags_for_article(conn, article_id)
    print("=" * 80)
    print(f"Title:       {row['title']}")
    print(f"Source:      {row['source_name']} ({row['source_type']})")
    print(f"URL:         {row['url']}")
    print(f"Published:   {row['published_at']}")
    print(f"Fetched:     {row['fetched_at']}")
    print(f"Status:      {row['status']}")
    print(f"Tags:        {', '.join(article_tags) if article_tags else '(none)'}")
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


def show_tags(conn: sqlite3.Connection):
    rows = conn.execute(
        "SELECT tag, COUNT(*) as count FROM tags GROUP BY tag ORDER BY count DESC"
    ).fetchall()

    if not rows:
        print("No tags yet. Run 'python categorize_articles.py' first.")
        return

    print("Tags in use:\n")
    for row in rows:
        print(f"  {row['tag']:<25} {row['count']}")
    print(f"\nTip: use --tag <name> to list articles with that tag.")


def main():
    parser = argparse.ArgumentParser(description="Browse articles in pipeline.db")
    parser.add_argument("--source", help="Filter by source name (partial match OK)")
    parser.add_argument("--search", help="Filter by keyword in title or text")
    parser.add_argument("--tag", help="Filter by tag (e.g. ransomware, hipaa)")
    parser.add_argument("--id", type=int, help="Show full details for one article by id")
    parser.add_argument("--counts", action="store_true", help="Show article counts per source")
    parser.add_argument("--tags", action="store_true", help="Show all tags and their counts")
    args = parser.parse_args()

    conn = get_connection()
    try:
        if args.id is not None:
            show_article(conn, args.id)
        elif args.counts:
            show_counts(conn)
        elif args.tags:
            show_tags(conn)
        else:
            list_articles(conn, args.source, args.search, args.tag)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
