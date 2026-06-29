"""
Shared contract for all scanner modules.

Every source (RSS, specific sites, Google Alerts, general web search, etc.)
implements the Scanner protocol below and returns a list of Article dicts.
This is the ONLY thing that makes the system modular: as long as a new
module returns Articles in this shape, nothing else in the pipeline needs
to change to support it.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Protocol


@dataclass
class Article:
    url: str
    title: str
    text: str
    source_name: str        # human-readable, e.g. "Krebs on Security"
    source_type: str        # "rss" | "specific_site" | "google_alert" | "general_web"
    published_at: Optional[str] = None   # ISO 8601 string if known, else None
    fetched_at: str = ""    # ISO 8601 string, set automatically if blank
    raw_html_path: Optional[str] = None  # path to saved raw HTML, if kept

    def __post_init__(self):
        if not self.fetched_at:
            self.fetched_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


class Scanner(Protocol):
    """Any scanner module must implement this."""

    name: str  # short identifier for logging, e.g. "rss"

    def fetch(self) -> list[Article]:
        """Return newly found articles. Should not raise on a single
        source failing -- log and continue, return what succeeded."""
        ...
