import re

from extraction.extract_emails import extract_emails
from extraction.extract_phones import extract_phones
from extraction.extract_names import extract_names
from extraction.classify_contact import classify_contact



def extract_contacts(provider, text, source_url):
	results = []

	patterns = [
		r".{0,300}privacy officer.{0,300}",
		r".{0,300}compliance officer.{0,300}",
		r".{0,300}HIPAA.{0,300}",
	]

	for pattern in patterns:
		for match in re.finditer(pattern, text, re.IGNORECASE):
			snippet = match.group()

			emails = extract_emails(snippet)
			phones = extract_phones(snippet)
			names = extract_names(snippet)

			for email in emails:
				name = names[0] if names else {}

				results.append({
					"provider_name": provider["provider_name"],
					"breach_submission_dates": provider["breach_submission_dates"],
					"website": provider["website"],
					"root_domain": provider["root_domain"],
					"first_name": name.get("first_name", ""),
					"last_name": name.get("last_name", ""),
					"email": email,
					"phone": "; ".join(phones),
					"source_url": source_url,
					"found_via": "site crawl",
					"context_snippet": snippet[:300],
					"contact_type": classify_contact(email, snippet),
				})

	return results