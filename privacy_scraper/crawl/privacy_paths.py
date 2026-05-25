from constants import PRIVACY_PATHS



def build_privacy_urls(base_url):
	urls = []

	for path in PRIVACY_PATHS:
		urls.append(base_url.rstrip("/") + path)

	return urls