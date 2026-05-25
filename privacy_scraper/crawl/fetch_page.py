import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT, USER_AGENT


SESSION = requests.Session()



def fetch_page_text(url):
	headers = {
		"User-Agent": USER_AGENT,
	}

	response = SESSION.get(
		url,
		headers=headers,
		timeout=REQUEST_TIMEOUT,
	)

	if response.status_code != 200:
		return None

	soup = BeautifulSoup(response.text, "html.parser")

	for tag in soup(["script", "style", "nav", "footer", "header"]):
		tag.decompose()

	return soup.get_text(" ", strip=True)