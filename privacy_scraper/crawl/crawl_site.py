from crawl.fetch_page import fetch_page_text
from crawl.privacy_paths import build_privacy_urls
from extraction.extract_contacts import extract_contacts



def crawl_provider_site(provider):
	contacts = []

	website = provider["website"]

	for url in build_privacy_urls(website):
		text = fetch_page_text(url)

		if not text:
			continue

		results = extract_contacts(
			provider=provider,
			text=text,
			source_url=url,
		)

		contacts.extend(results)

	return contacts