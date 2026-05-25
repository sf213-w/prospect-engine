from urllib.parse import urlparse

from constants import BAD_DOMAINS
from search.ddg_search import ddg_search



def extract_root_domain(url):
	parsed = urlparse(url)
	host = parsed.netloc.lower().replace("www.", "")

	parts = host.split(".")

	if len(parts) >= 2:
		return ".".join(parts[-2:])

	return host



def is_valid_domain(url):
	return not any(domain in url for domain in BAD_DOMAINS)



def find_official_website(provider_name):
	queries = [
		f'"{provider_name}" official site',
		f'"{provider_name}" privacy officer',
	]

	for query in queries:
		results = ddg_search(query)

		for result in results:
			url = result.get("href") or result.get("url")

			if not url:
				continue

			if not is_valid_domain(url):
				continue

			parsed = urlparse(url)

			return {
				"website": f"{parsed.scheme}://{parsed.netloc}",
				"root_domain": extract_root_domain(url),
			}

	return None