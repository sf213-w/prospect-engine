"""
Applies the rule-based categorizer to articles in pipeline.db.

By default, only tags articles with status='new' (i.e. not yet categorized).
Use --recategorize-all to wipe and reapply tags to every article -- useful
after editing config/tag_rules.yaml, since rule changes don't retroactively
apply to already-categorized articles otherwise.

Usage:
    python categorize_articles.py
    python categorize_articles.py --recategorize-all
"""

from __future__ import annotations
import argparse
import logging

from categorizer import Categorizer
from storage.db import (
    get_connection,
    get_uncategorized_articles,
    set_article_tags,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("categorize_articles")


def get_all_articles(conn):
    return conn.execute("SELECT id, title, text FROM articles").fetchall()


def main():
    parser = argparse.ArgumentParser(description="Categorize articles using keyword rules")
    parser.add_argument(
        "--recategorize-all",
        action="store_true",
        help="Reapply rules to every article, not just uncategorized ones",
    )
    args = parser.parse_args()

    cat = Categorizer()
    conn = get_connection()

    try:
        if args.recategorize_all:
            articles = get_all_articles(conn)
            logger.info("Recategorizing all %d articles", len(articles))
        else:
            articles = get_uncategorized_articles(conn)
            logger.info("Categorizing %d new articles", len(articles))

        tagged_count = 0
        no_match_count = 0

        for article in articles:
            tags = cat.categorize_text(article["title"], article["text"])
            set_article_tags(conn, article["id"], tags)
            if tags:
                tagged_count += 1
            else:
                no_match_count += 1

        logger.info(
            "Done. %d articles tagged, %d articles matched no rules.",
            tagged_count,
            no_match_count,
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
