#!/usr/bin/env python3
"""
Healthcare Compliance News Intelligence — Ollama Edition
Fetches raw content directly from US government enforcement sources,
then uses a local Ollama model to parse, classify, and summarise stories.

Dependencies: pip install requests beautifulsoup4 ollama
Requires:     ollama running locally (default: http://localhost:11434)
"""

import json
import argparse
import sys
import time
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

try:
    import ollama as ollama_sdk
    OLLAMA_SDK = True
except ImportError:
    OLLAMA_SDK = False

# ── Source definitions ────────────────────────────────────────────────────────
# Each source: url, fetch strategy, domain tag, category hint

SOURCES = {
    "hipaa": [
        {
            "name": "HHS OCR Breach Portal",
            "url": "https://ocrportal.hhs.gov/ocr/breach/breach_report.jsf",
            "fallback_url": "https://www.hhs.gov/hipaa/for-professionals/breach-notification/breach-reporting/index.html",
            "strategy": "html",
            "domain": "hipaa",
            "category": "news",
        },
        {
            "name": "HHS OCR Resolution Agreements",
            "url": "https://www.hhs.gov/hipaa/for-professionals/compliance-enforcement/agreements/index.html",
            "fallback_url": "https://www.hhs.gov/hipaa/for-professionals/compliance-enforcement/enforcement-highlights/index.html",
            "strategy": "html",
            "domain": "hipaa",
            "category": "news",
        },
        {
            "name": "HHS OCR Press Releases",
            "url": "https://www.hhs.gov/about/news/index.html?q=hipaa&submit=Search",
            "fallback_url": "https://www.hhs.gov/hipaa/for-professionals/compliance-enforcement/agreements/index.html",
            "strategy": "html",
            "domain": "hipaa",
            "category": "news",
        },
        {
            "name": "Federal Register – HIPAA",
            "url": "https://www.federalregister.gov/api/v1/documents.json?agencies[]=civil-rights-office&order=newest&per_page=10",
            "strategy": "json_api",
            "domain": "hipaa",
            "category": "advice",
        },
        {
            "name": "Maine AG Breach Database",
            "url": "https://www.maine.gov/agviewer/content/ag/985235c7-cb95-819f-e996-b8f2f779ef3e/forms/acknowledgement.html",
            "strategy": "html",
            "domain": "hipaa",
            "category": "news",
        },
    ],
    "cyber": [
        {
            "name": "HC3 Healthcare Cybersecurity",
            "url": "https://www.hhs.gov/about/agencies/asa/ocio/hc3/index.html",
            "strategy": "html",
            "domain": "cyber",
            "category": "news",
        },
        {
            "name": "CISA Healthcare Advisories",
            "url": "https://www.cisa.gov/news-events/cybersecurity-advisories?f%5B0%5D=advisory_type%3A94",
            "strategy": "html",
            "domain": "cyber",
            "category": "news",
        },
        {
            "name": "DOJ Healthcare Data Breach Press Releases",
            "url": "https://www.justice.gov/news?q=healthcare+data+breach&op=Search",
            "strategy": "html",
            "domain": "cyber",
            "category": "news",
        },
    ],
    "osha": [
        {
            "name": "OSHA Press Releases",
            "url": "https://www.osha.gov/news/newsreleases",
            "strategy": "html",
            "domain": "osha",
            "category": "news",
        },
    ],
    "fraud": [
        {
            "name": "DOJ Health Care Fraud Unit",
            "url": "https://www.justice.gov/criminal/criminal-fraud/health-care-fraud-unit",
            "strategy": "html",
            "domain": "fraud",
            "category": "news",
        },
        {
            "name": "HHS OIG Fraud Alerts",
            "url": "https://oig.hhs.gov/compliance/alerts/",
            "strategy": "html",
            "domain": "fraud",
            "category": "news",
        },
        {
            "name": "HHS OIG Enforcement Actions",
            "url": "https://oig.hhs.gov/fraud/enforcement/",
            "strategy": "html",
            "domain": "fraud",
            "category": "news",
        },
    ],
    "ethics": [
        {
            "name": "Texas Medical Board Actions",
            "url": "https://www.tmb.state.tx.us/page/disciplinary-actions",
            "strategy": "html",
            "domain": "ethics",
            "category": "news",
        },
        {
            "name": "California Medical Board Actions",
            "url": "https://www.mbc.ca.gov/About/News/Press_Releases/",
            "strategy": "html",
            "domain": "ethics",
            "category": "news",
        },
    ],
    "eeoc": [
        {
            "name": "EEOC Healthcare Press Releases",
            "url": "https://www.eeoc.gov/newsroom/search?q=healthcare&type=pressrelease",
            "strategy": "html",
            "domain": "eeoc",
            "category": "news",
        },
    ],
}

DOMAIN_LABELS = {
    "all":    "All domains",
    "hipaa":  "HIPAA & Privacy",
    "cyber":  "Cybersecurity",
    "osha":   "OSHA & Safety",
    "fraud":  "Fraud & Abuse",
    "ethics": "Ethics & Licensing",
    "eeoc":   "Workplace & EEOC",
}

CATEGORY_LABELS = {
    "news":   "Breaking News",
    "advice": "Trend / Advice",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ComplianceIntelligenceBot/1.0; research purposes)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Source fetchers ───────────────────────────────────────────────────────────

def fetch_html(url: str, timeout: int = 15) -> str:
    """Fetch a page and return cleaned visible text (max 6000 chars).
    Falls back to verify=False on SSL errors (some .gov sites have cert issues).
    """
    import ssl
    import urllib3

    def _parse(r) -> str:
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:6000]

    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return _parse(r)
    except requests.exceptions.SSLError:
        # SSL failure — retry without verification (warn but continue)
        try:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            r = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
            r.raise_for_status()
            return _parse(r)
        except Exception as e2:
            return f"[SSL fallback also failed for {url}: {e2}]"
    except requests.exceptions.ConnectionError as e:
        return f"[Connection error for {url}: {e}]"
    except requests.exceptions.Timeout:
        return f"[Timeout fetching {url}]"
    except Exception as e:
        return f"[Could not fetch {url}: {e}]"


def fetch_json_api(url: str, timeout: int = 15) -> str:
    """Fetch a JSON API endpoint and return a readable summary."""
    try:
        r = requests.get(url, headers={**HEADERS, "Accept": "application/json"}, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        # Federal Register returns {results: [...]}
        results = data.get("results", data if isinstance(data, list) else [])
        lines = []
        for item in results[:15]:
            title = item.get("title", "")
            date  = item.get("publication_date", item.get("date", ""))
            doc_type = item.get("type", "")
            abstract = item.get("abstract", "")[:300]
            lines.append(f"- [{date}] {doc_type}: {title}\n  {abstract}")
        return "\n".join(lines)[:5000]
    except Exception as e:
        return f"[Could not fetch JSON from {url}: {e}]"


def fetch_source(source: dict) -> str:
    strategy = source.get("strategy", "html")
    url = source.get("url")
    if strategy == "json_api":
        return fetch_json_api(url)
    result = fetch_html(url)
    # If primary failed and a fallback is defined, try it
    if result.startswith("[") and source.get("fallback_url"):
        fallback = source["fallback_url"]
        result2 = fetch_html(fallback)
        if not result2.startswith("["):
            return result2
    return result


# ── Ollama interaction ────────────────────────────────────────────────────────

def list_ollama_models(host: str) -> list[str]:
    """Return list of locally available model names."""
    try:
        r = requests.get(f"{host}/api/tags", timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def call_ollama(prompt: str, model: str, host: str, timeout: int = 120) -> str:
    """Call Ollama via REST API and return the response text."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 4096},
    }
    r = requests.post(f"{host}/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json().get("response", "")


def build_prompt(raw_content: str, source_name: str, domain: str,
                 categories: list[str], max_results: int) -> str:
    if set(categories) == {"news", "advice"}:
        type_desc = "breaking news items OR trend/advice pieces"
    elif "news" in categories:
        type_desc = "breaking news items only"
    else:
        type_desc = "trend/advice pieces only"

    return f"""You are a healthcare compliance intelligence analyst. Below is raw content scraped from "{source_name}" — a US government or legal enforcement source.

Extract up to {max_results} distinct {type_desc} relevant to healthcare compliance teams. Focus on enforcement actions, breach reports, settlements, penalties, regulatory guidance, or cybersecurity threats.

Return ONLY a valid JSON array. No markdown, no explanation, no preamble. If there is nothing relevant, return [].

Each item schema:
{{
  "title": "Specific factual headline",
  "category": "news" or "advice",
  "domain": "{domain}",
  "source": "{source_name}",
  "date": "date or month/year string, or null",
  "summary": "2-3 sentences on what happened and why it matters",
  "tags": ["2 to 4 tags"],
  "penalty": "dollar amount string if enforcement action, else null",
  "url": null
}}

--- RAW CONTENT START ---
{raw_content}
--- RAW CONTENT END ---

Return ONLY the JSON array:"""


# ── Core pipeline ─────────────────────────────────────────────────────────────

def fetch_stories(
    domain: str = "all",
    categories: list[str] = None,
    max_results: int = 10,
    model: str = "llama3",
    host: str = "http://localhost:11434",
    verbose: bool = False,
) -> list[dict]:
    if categories is None:
        categories = ["news", "advice"]

    # Select sources
    if domain == "all":
        sources = [s for group in SOURCES.values() for s in group]
    else:
        sources = SOURCES.get(domain, [])

    if not sources:
        raise ValueError(f"No sources configured for domain: {domain}")

    # Filter sources by requested categories
    sources = [s for s in sources if s["category"] in categories]
    if not sources:
        sources_unfiltered = SOURCES.get(domain, [s for g in SOURCES.values() for s in g])
        sources = sources_unfiltered  # fall back to all

    all_stories = []
    per_source = max(2, max_results // max(len(sources), 1) + 1)

    for src in sources:
        print(f"  Fetching: {src['name']} ...", flush=True)
        raw = fetch_source(src)

        if raw.startswith("[") and ("Could not fetch" in raw or "failed" in raw.lower() or
                                    "Timeout" in raw or "Connection error" in raw or
                                    "SSL" in raw):
            print(f"    ⚠ Skipping — {raw[:120]}", flush=True)
            continue

        if verbose:
            print(f"    Got {len(raw)} chars")

        prompt = build_prompt(raw, src["name"], src["domain"], categories, per_source)

        print(f"  Analysing with {model} ...", flush=True)
        try:
            response = call_ollama(prompt, model, host)
            # Extract JSON array from response
            start = response.find("[")
            end   = response.rfind("]") + 1
            if start == -1 or end == 0:
                if verbose:
                    print(f"    ⚠ No JSON array in response")
                continue
            items = json.loads(response[start:end])
            # Filter by requested categories
            items = [i for i in items if i.get("category") in categories]
            all_stories.extend(items)
            if verbose:
                print(f"    → {len(items)} stories extracted")
        except json.JSONDecodeError as e:
            if verbose:
                print(f"    ⚠ JSON parse error: {e}")
        except requests.exceptions.Timeout:
            print(f"    ⚠ Ollama timed out on {src['name']} — try a smaller/faster model")
        except Exception as e:
            if verbose:
                print(f"    ⚠ Error: {e}")

        # Pace requests so we don't hammer sources
        time.sleep(0.5)

    # Deduplicate by title similarity and cap to max_results
    seen_titles = set()
    unique = []
    for story in all_stories:
        key = re.sub(r"[^a-z0-9]", "", story.get("title", "").lower())[:60]
        if key and key not in seen_titles:
            seen_titles.add(key)
            unique.append(story)

    return unique[:max_results]


# ── Output formatters ─────────────────────────────────────────────────────────

def print_terminal(stories: list[dict], domain: str, categories: list[str], model: str) -> None:
    width = 72
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    print()
    print("=" * width)
    print("  HEALTHCARE COMPLIANCE INTELLIGENCE REPORT")
    print(f"  Domain : {DOMAIN_LABELS.get(domain, domain)}")
    print(f"  Types  : {', '.join(CATEGORY_LABELS[c] for c in categories)}")
    print(f"  Model  : {model} (local Ollama)")
    print(f"  Run at : {now}")
    print("=" * width)

    news_count   = sum(1 for s in stories if s.get("category") == "news")
    advice_count = sum(1 for s in stories if s.get("category") == "advice")
    sources      = {s.get("source", "Unknown") for s in stories}

    print(f"\n  {len(stories)} stories  |  {news_count} news  |  {advice_count} advice  |  {len(sources)} sources\n")
    print("-" * width)

    for i, story in enumerate(stories, 1):
        cat     = story.get("category", "news")
        label   = "[NEWS]  " if cat == "news" else "[ADVICE]"
        title   = story.get("title", "Untitled")
        source  = story.get("source", "Unknown")
        date    = story.get("date") or ""
        penalty = story.get("penalty")
        summary = story.get("summary", "")
        tags    = story.get("tags", [])
        url     = story.get("url")

        print(f"\n{i:>2}. {label}  {title}")
        print(f"     Source: {source}" + (f"  |  {date}" if date else ""))
        if penalty:
            print(f"     Penalty: {penalty}")
        print()
        words = summary.split()
        line, lines = [], []
        for w in words:
            if len(" ".join(line + [w])) > 66:
                lines.append("     " + " ".join(line))
                line = [w]
            else:
                line.append(w)
        if line:
            lines.append("     " + " ".join(line))
        print("\n".join(lines))
        if tags:
            print(f"\n     Tags: {' · '.join(tags)}")
        if url:
            print(f"     URL : {url}")
        print()
        print("-" * width)
    print()


def save_json(stories: list[dict], path: str, model: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "model": model,
            "stories": stories,
        }, f, indent=2)
    print(f"  → Saved JSON: {path}")


def save_markdown(stories: list[dict], domain: str, categories: list[str],
                  path: str, model: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Healthcare Compliance Intelligence Report",
        "",
        f"**Domain:** {DOMAIN_LABELS.get(domain, domain)}  ",
        f"**Types:** {', '.join(CATEGORY_LABELS[c] for c in categories)}  ",
        f"**Model:** {model} (local Ollama)  ",
        f"**Generated:** {now}",
        "",
        "---",
        "",
    ]
    for i, story in enumerate(stories, 1):
        cat     = story.get("category", "news")
        label   = "🔴 Breaking News" if cat == "news" else "🟢 Trend / Advice"
        title   = story.get("title", "Untitled")
        source  = story.get("source", "")
        date    = story.get("date") or ""
        penalty = story.get("penalty")
        summary = story.get("summary", "")
        tags    = story.get("tags", [])
        url     = story.get("url")

        lines += [f"## {i}. {title}", "",
                  f"**{label}** · {source}" + (f" · {date}" if date else "")]
        if penalty:
            lines.append(f"**Penalty/Settlement:** {penalty}")
        lines += ["", summary, ""]
        if tags:
            lines.append(f"**Tags:** {' · '.join(tags)}")
        if url:
            lines.append(f"**Source:** [{url}]({url})")
        lines += ["", "---", ""]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  → Saved Markdown: {path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Healthcare Compliance Intelligence — local Ollama edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python hipaa_intelligence_ollama.py
  python hipaa_intelligence_ollama.py --model mistral
  python hipaa_intelligence_ollama.py --domain cyber --type news
  python hipaa_intelligence_ollama.py --domain fraud --results 8 --output report.md
  python hipaa_intelligence_ollama.py --list-models

Domains: all, hipaa, cyber, osha, fraud, ethics, eeoc
Types:   news, advice, both (default: both)
Models:  any model you have pulled in Ollama (llama3, mistral, gemma3, phi3, etc.)
        """,
    )
    parser.add_argument("--domain", "-d", choices=["all","hipaa","cyber","osha","fraud","ethics","eeoc"],
                        default="all", help="Regulatory domain (default: all)")
    parser.add_argument("--type", "-t", choices=["news","advice","both"],
                        default="both", help="Story category (default: both)")
    parser.add_argument("--results", "-n", type=int, default=10,
                        help="Max stories to return (default: 10)")
    parser.add_argument("--model", "-m", default="llama3",
                        help="Ollama model name (default: llama3)")
    parser.add_argument("--host", default="http://localhost:11434",
                        help="Ollama host (default: http://localhost:11434)")
    parser.add_argument("--output", "-o", default=None,
                        help="Save to file (.json or .md). Defaults to timestamped .md in current directory.")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show fetch/parse details")
    parser.add_argument("--list-models", action="store_true",
                        help="List available Ollama models and exit")

    args = parser.parse_args()

    # List models mode
    if args.list_models:
        models = list_ollama_models(args.host)
        if models:
            print("\nAvailable Ollama models:")
            for m in models:
                print(f"  • {m}")
        else:
            print(f"\nNo models found — is Ollama running at {args.host}?")
        sys.exit(0)

    # Check Ollama is reachable
    models = list_ollama_models(args.host)
    if not models:
        print(f"\nError: Cannot reach Ollama at {args.host}", file=sys.stderr)
        print("Make sure Ollama is running:  ollama serve", file=sys.stderr)
        sys.exit(1)

    # Normalise model name: "llama3.2" matches "llama3.2:latest"
    def _normalise(m: str) -> str:
        return m.split(":")[0].lower()

    model_arg = args.model
    available_bases = [_normalise(m) for m in models]
    if _normalise(model_arg) in available_bases:
        # Resolve to the full tag Ollama knows (e.g. "llama3.2:latest")
        idx = available_bases.index(_normalise(model_arg))
        model_arg = models[idx]
    else:
        print(f"\nWarning: model '{model_arg}' not found locally.")
        print(f"Available: {', '.join(models)}")
        print(f"Pull it with:  ollama pull {model_arg}\n")

    args.model = model_arg

    categories = ["news", "advice"] if args.type == "both" else [args.type]

    print(f"\n{'='*60}")
    print(f"  Domain : {DOMAIN_LABELS[args.domain]}")
    print(f"  Types  : {', '.join(CATEGORY_LABELS[c] for c in categories)}")
    print(f"  Model  : {args.model}  |  Host: {args.host}")
    print(f"{'='*60}\n")

    try:
        stories = fetch_stories(
            domain=args.domain,
            categories=categories,
            max_results=args.results,
            model=args.model,
            host=args.host,
            verbose=args.verbose,
        )
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)

    if not stories:
        print("\nNo stories extracted. Try --verbose to debug, or a different domain.")
        sys.exit(0)

    # Auto-generate output filename if not specified
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"compliance_report_{timestamp}.md"
        print(f"  Output : {args.output} (auto-generated)\n")

    if args.output:
        if args.output.endswith(".json"):
            save_json(stories, args.output, args.model)
        elif args.output.endswith(".md"):
            save_markdown(stories, args.domain, categories, args.output, args.model)
        else:
            print("Output must be .json or .md")
            sys.exit(1)

    print_terminal(stories, args.domain, categories, args.model)


if __name__ == "__main__":
    main()