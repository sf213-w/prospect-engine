from dataclasses import dataclass, field
from typing import List


@dataclass
class Provider:
	provider_name: str
	breach_submission_dates: List[str] = field(default_factory=list)
	website: str = ""
	root_domain: str = ""


@dataclass
class Contact:
	provider_name: str
	breach_submission_dates: List[str]
	website: str
	root_domain: str

	first_name: str = ""
	last_name: str = ""

	email: str = ""
	normalized_email: str = ""
	email_domain: str = ""

	phone: str = ""

	source_url: str = ""
	found_via: str = ""
	context_snippet: str = ""

	contact_type: str = "unknown"
	contact_confidence: int = 0
	contact_score: int = 0