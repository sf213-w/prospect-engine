"""
Rule-based categorizer.

Loads keyword rules from config/tag_rules.yaml and tags articles based on
whether any keyword for a tag appears in the article's title or text
(case-insensitive substring match). An article can receive multiple tags,
or none if nothing matches.

Usage:
    from categorizer import Categorizer
    cat = Categorizer()
    tags = cat.categorize_text(title, text)   # -> list[str]
"""

from __future__ import annotations
from pathlib import Path

import yaml

DEFAULT_RULES_PATH = Path(__file__).parent / "config" / "tag_rules.yaml"


class Categorizer:
    def __init__(self, rules_path: Path = DEFAULT_RULES_PATH):
        self.rules_path = rules_path
        self.rules = self._load_rules()

    def _load_rules(self) -> dict[str, list[str]]:
        with open(self.rules_path, "r") as f:
            raw = yaml.safe_load(f) or {}
        # Normalize keywords to lowercase once, up front, so matching is cheap
        return {
            tag: [kw.lower() for kw in keywords]
            for tag, keywords in raw.items()
        }

    def categorize_text(self, title: str | None, text: str | None) -> list[str]:
        """Return the list of tags that match this article's title+text."""
        haystack = f"{title or ''} {text or ''}".lower()

        matched = []
        for tag, keywords in self.rules.items():
            if any(keyword in haystack for keyword in keywords):
                matched.append(tag)
        return matched
