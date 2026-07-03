"""
Web UI for the news pipeline.

Run with:
    python app.py

Then open http://localhost:5000 in your browser.
"""

from __future__ import annotations
import json
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, session, Response

from ollama_client import generate, OllamaError, DEFAULT_MODEL
from prompt_builder import build_prompt
from storage.db import (
    get_connection, init_db,
    get_all_tags_with_counts,
    get_articles_by_ids,
    save_story_run,
    get_story_run,
    list_story_runs,
)

app = Flask(__name__)
app.secret_key = "news-pipeline-local-secret"  # only used for flash messages

STORIES_DIR = Path(__file__).parent / "stories"
STORIES_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_db():
    return get_connection()


def fetch_articles(source=None, search=None, tags=None):
    """Fetch articles, optionally filtered by a list of tags (AND logic —
    articles must carry ALL of the selected tags), source, and search term."""
    conn = get_db()

    conditions, params = [], []

    if tags:
        # For each required tag, the article must have a matching tags row.
        # One EXISTS subquery per tag gives clean AND semantics.
        for tag in tags:
            conditions.append(
                "EXISTS (SELECT 1 FROM tags t WHERE t.article_id = a.id AND t.tag = ?)"
            )
            params.append(tag)

    if source:
        conditions.append("a.source_name LIKE ?")
        params.append(f"%{source}%")

    if search:
        conditions.append("(a.title LIKE ? OR a.text LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    query = f"""
        SELECT a.id, a.title, a.source_name, a.published_at, a.url, a.status
        FROM articles a
        {where}
        ORDER BY a.fetched_at DESC
    """

    rows = conn.execute(query, params).fetchall()

    result = []
    for row in rows:
        row_tags = [r["tag"] for r in conn.execute(
            "SELECT tag FROM tags WHERE article_id = ? ORDER BY tag", (row["id"],)
        ).fetchall()]
        result.append({"id": row["id"], "title": row["title"],
                       "source_name": row["source_name"],
                       "published_at": row["published_at"],
                       "url": row["url"], "status": row["status"],
                       "tags": row_tags})
    conn.close()
    return result


def get_selected_ids() -> list[int]:
    """Read the current article selection from the session."""
    return session.get("selected_ids", [])


def set_selected_ids(ids: list[int]):
    session["selected_ids"] = ids
    session.modified = True


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Article browser with tag sidebar and filter bar."""
    # getlist handles ?tag=ransomware&tag=hipaa -> ['ransomware', 'hipaa']
    active_tags = request.args.getlist("tag")
    source      = request.args.get("source", "").strip() or None
    search      = request.args.get("search", "").strip() or None

    articles = fetch_articles(source=source, search=search, tags=active_tags)

    conn = get_db()
    all_tags = [dict(r) for r in get_all_tags_with_counts(conn)]
    sources  = [r[0] for r in conn.execute(
        "SELECT DISTINCT source_name FROM articles ORDER BY source_name"
    ).fetchall()]
    total_articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    conn.close()

    selected_ids = get_selected_ids()

    return render_template("index.html",
        articles=articles, all_tags=all_tags, sources=sources,
        selected_ids=selected_ids, total_articles=total_articles,
        active_tags=active_tags, active_source=source, active_search=search)


@app.route("/select", methods=["POST"])
def select():
    """Add/remove articles from the current selection."""
    action  = request.form.get("action")          # "add", "remove", "clear", "set"
    ids_raw = request.form.get("ids", "")
    ids     = [int(x) for x in ids_raw.split(",") if x.strip().isdigit()]

    current = get_selected_ids()

    if action == "add":
        current = list(dict.fromkeys(current + ids))  # deduplicate, preserve order
    elif action == "remove":
        current = [i for i in current if i not in ids]
    elif action == "clear":
        current = []
    elif action == "set":
        current = ids

    set_selected_ids(current)
    return redirect(request.referrer or url_for("index"))


@app.route("/generate", methods=["GET", "POST"])
def generate_story():
    """Generation parameters form and story output."""
    selected_ids = get_selected_ids()
    conn = get_db()
    selected_articles = [dict(r) for r in get_articles_by_ids(conn, selected_ids)]
    conn.close()

    error = None
    story = None
    run_id = None

    if request.method == "POST":
        topic    = request.form.get("topic", "").strip() or None
        title    = request.form.get("title", "").strip() or None
        length   = int(request.form.get("length", 400))
        tone     = request.form.get("tone", "").strip() or None
        audience = request.form.get("audience", "").strip() or None
        angle    = request.form.get("angle", "").strip() or None
        model    = request.form.get("model", DEFAULT_MODEL).strip()

        if not selected_articles:
            error = "No articles selected. Go back to the browser and select some articles first."
        else:
            # convert dicts back to Row-compatible objects for prompt_builder
            class RowProxy:
                def __init__(self, d): self._d = d
                def __getitem__(self, k): return self._d[k]

            proxies = [RowProxy(a) for a in selected_articles]
            prompt  = build_prompt(proxies, topic=topic, title=title,
                                   length_words=length, tone=tone,
                                   audience=audience, angle=angle)
            try:
                story = generate(prompt, model=model)
                conn  = get_db()
                run_id = save_story_run(conn, selected_ids,
                    {"topic": topic, "title": title, "length_words": length,
                     "tone": tone, "audience": audience, "angle": angle, "model": model},
                    story)
                conn.close()
            except OllamaError as e:
                error = str(e)

    return render_template("generate.html",
        selected_articles=selected_articles,
        story=story, run_id=run_id, error=error,
        default_model=DEFAULT_MODEL)


@app.route("/story/<int:run_id>")
def view_story(run_id):
    """View a previously generated story."""
    conn = get_db()
    run  = get_story_run(conn, run_id)
    if not run:
        conn.close()
        return "Story not found.", 404

    article_ids = json.loads(run["article_ids"])
    articles    = [dict(r) for r in get_articles_by_ids(conn, article_ids)]
    parameters  = json.loads(run["parameters"])
    conn.close()

    return render_template("story.html",
        run=dict(run), articles=articles, parameters=parameters)


@app.route("/story/<int:run_id>/download")
def download_story(run_id):
    """Download a story as a plain text file."""
    conn = get_db()
    run  = get_story_run(conn, run_id)
    conn.close()
    if not run:
        return "Story not found.", 404
    filename = f"story_{run_id}.txt"
    return Response(run["output_text"],
                    mimetype="text/plain",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.route("/stories")
def stories():
    """History of all generated stories."""
    conn = get_db()
    runs = []
    for r in list_story_runs(conn):
        params = json.loads(r["parameters"])
        runs.append({
            "id": r["id"],
            "created_at": r["created_at"][:19].replace("T", " "),
            "title": params.get("title") or params.get("topic") or "(untitled)",
            "model": params.get("model", ""),
            "article_count": len(json.loads(r["article_ids"])),
        })
    conn.close()
    return render_template("stories.html", runs=runs)


# ---------------------------------------------------------------------------
# Dev server entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    print("Starting news pipeline UI at http://localhost:5000")
    app.run(debug=True, port=5000)
