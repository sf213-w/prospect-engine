"""
Generate a news story from selected source articles using a local Ollama model.

Select source articles by tag and/or specific ids, supply generation
parameters, and this calls your local Ollama instance to synthesize a
story from them. The result is printed, optionally saved to a file, and
always recorded in the story_runs table for later reference.

Usage examples:
    # Select by tag, basic generation
    python generate_story.py --tag ransomware --length 400

    # Select specific articles by id
    python generate_story.py --ids 3,7,12 --title "Local Clinics Targeted in Wave of Breaches"

    # Combine tag + extra params
    python generate_story.py --tag hipaa --tag small_business --topic "what small practices should do" \\
        --tone "urgent but practical" --audience "small medical practice owners" --length 500

    # Save output to a file
    python generate_story.py --tag ransomware --save output.md

    # Use a different model
    python generate_story.py --tag ransomware --model mistral
"""

from __future__ import annotations
import argparse
import logging
import sys

from ollama_client import generate, OllamaError, DEFAULT_MODEL
from prompt_builder import build_prompt
from storage.db import get_connection, get_articles_by_ids, save_story_run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("generate_story")


def select_articles_by_tags(conn, tags: list[str]) -> list:
    """Articles matching ANY of the given tags (union, not intersection),
    deduplicated. If you select by multiple tags, you get the broader set --
    use --ids if you need a precise hand-picked combination instead."""
    if not tags:
        return []
    placeholders = ",".join("?" for _ in tags)
    rows = conn.execute(
        f"""
        SELECT DISTINCT a.* FROM articles a
        JOIN tags t ON a.id = t.article_id
        WHERE t.tag IN ({placeholders})
        ORDER BY a.fetched_at DESC
        """,
        tags,
    ).fetchall()
    return rows


def parse_ids(ids_str: str) -> list[int]:
    try:
        return [int(x.strip()) for x in ids_str.split(",") if x.strip()]
    except ValueError:
        raise SystemExit(f"--ids must be comma-separated numbers, got: {ids_str!r}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate a news story from selected articles via Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--tag", action="append", default=[],
        help="Select articles with this tag. Can be repeated for multiple tags (union).",
    )
    parser.add_argument(
        "--ids", help="Comma-separated article ids to use as source material, e.g. 3,7,12",
    )
    parser.add_argument("--topic", help="Specific topic/focus for the story")
    parser.add_argument("--title", help="Exact headline to use (otherwise the model writes one)")
    parser.add_argument("--length", type=int, default=400, help="Target length in words (default: 400)")
    parser.add_argument("--tone", help="Desired tone, e.g. 'urgent but not alarmist'")
    parser.add_argument("--audience", help="Target audience, e.g. 'small business owners with no IT staff'")
    parser.add_argument("--angle", help="Specific angle or emphasis for the story")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--save", help="Also save the generated story to this file path")
    parser.add_argument(
        "--max-articles", type=int, default=15,
        help="Safety cap on number of source articles to include (default: 15, to avoid huge prompts)",
    )

    args = parser.parse_args()

    if not args.tag and not args.ids:
        parser.error("You must select source articles with --tag and/or --ids")

    conn = get_connection()

    articles = []
    seen_ids = set()

    if args.tag:
        for row in select_articles_by_tags(conn, args.tag):
            if row["id"] not in seen_ids:
                articles.append(row)
                seen_ids.add(row["id"])

    if args.ids:
        ids = parse_ids(args.ids)
        for row in get_articles_by_ids(conn, ids):
            if row["id"] not in seen_ids:
                articles.append(row)
                seen_ids.add(row["id"])

    if not articles:
        conn.close()
        print("No articles matched your selection. Check your --tag/--ids values "
              "with 'python browse_articles.py --tags' or 'python browse_articles.py'.")
        sys.exit(1)

    if len(articles) > args.max_articles:
        logger.warning(
            "%d articles matched, trimming to the %d most recent (use --max-articles to change this)",
            len(articles), args.max_articles,
        )
        articles = articles[: args.max_articles]

    logger.info("Using %d source article(s): %s", len(articles), [a["id"] for a in articles])

    prompt = build_prompt(
        articles=articles,
        topic=args.topic,
        title=args.title,
        length_words=args.length,
        tone=args.tone,
        audience=args.audience,
        angle=args.angle,
    )

    logger.info("Sending prompt to Ollama (model: %s)...", args.model)
    try:
        story = generate(prompt, model=args.model)
    except OllamaError as e:
        conn.close()
        print(f"\nGeneration failed: {e}")
        sys.exit(1)

    parameters = {
        "topic": args.topic,
        "title": args.title,
        "length_words": args.length,
        "tone": args.tone,
        "audience": args.audience,
        "angle": args.angle,
        "model": args.model,
        "tags_used": args.tag,
    }
    run_id = save_story_run(conn, [a["id"] for a in articles], parameters, story)
    conn.close()

    print("\n" + "=" * 80)
    print(story)
    print("=" * 80)
    print(f"\nSaved as story_run #{run_id}")

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            f.write(story)
        print(f"Also saved to {args.save}")


if __name__ == "__main__":
    main()
