import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def fetch_homepage(url):

	try:
		headers = {"User-Agent": "Mozilla/5.0"}
		response = requests.get(url, headers=headers, timeout=10)

		if response.status_code == 200:
			return response.text
		else:
			print(f"Failed to fetch page: {response.status_code}")

	except Exception as e:
		print("Request error:", e)

	return None


def find_key_links(base_url, html):

	soup = BeautifulSoup(html, "html.parser")

	contact_links = []
	about_links = []
	team_links = []

	for link in soup.find_all("a", href=True):

		href = link["href"].lower()

		full_url = urljoin(base_url, href)

		if "contact" in href:
			contact_links.append(full_url)

		if "about" in href:
			about_links.append(full_url)

		if "team" in href or "staff" in href:
			team_links.append(full_url)

	return {
		"contact": list(set(contact_links)),
		"about": list(set(about_links)),
		"team": list(set(team_links))
	}


def crawl_website(url):

	print(f"\nCrawling: {url}")

	html = fetch_homepage(url)

	if html is None:
		print("Failed to download homepage.")
		return

	links = find_key_links(url, html)

	print("\nContact Pages:")
	for l in links["contact"]:
		print(l)

	print("\nAbout Pages:")
	for l in links["about"]:
		print(l)

	print("\nTeam Pages:")
	for l in links["team"]:
		print(l)


def main():

	url = input("Enter website URL: ").strip()

	crawl_website(url)


if __name__ == "__main__":
	main()