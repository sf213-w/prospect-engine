import requests
import re
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin


EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
PHONE_REGEX = r"\+?\d[\d\-\(\) ]{7,}\d"


def fetch_page(url):

	try:
		headers = {"User-Agent": "Mozilla/5.0"}
		response = requests.get(url, headers=headers, timeout=10)

		if response.status_code == 200:
			return response.text

	except Exception as e:
		print("Request failed:", e)

	return ""


def find_emails(text):

	emails = re.findall(EMAIL_REGEX, text)
	return list(set(emails))


def find_phones(text):

	phones = re.findall(PHONE_REGEX, text)
	return list(set(phones))


def extract_contact_link(soup, base_url):

	for link in soup.find_all("a", href=True):

		href = link["href"].lower()

		if "contact" in href:
			return urljoin(base_url, href)

	return None


def extract_title(soup):

	if soup.title:
		return soup.title.get_text().strip()

	return ""


def guess_person_name(text):

	lines = text.split("\n")

	for line in lines:

		line = line.strip()

		if len(line.split()) == 2 and line[0].isupper():
			return line

	return ""


def guess_location(text):

	city = ""
	state = ""

	pattern = r"([A-Z][a-z]+),\s*([A-Z]{2})"

	match = re.search(pattern, text)

	if match:
		city = match.group(1)
		state = match.group(2)

	return city, state


def build_lead(org_name, website):

	html = fetch_page(website)

	if html == "":
		return None

	soup = BeautifulSoup(html, "html.parser")

	text = soup.get_text(separator="\n")

	emails = find_emails(text)
	phones = find_phones(text)

	title = extract_title(soup)

	name_guess = guess_person_name(text)

	city, state = guess_location(text)

	contact_link = extract_contact_link(soup, website)

	row = {

		"Person - Marketing status": "",
		"Person - Double opt-in": "",

		"Person - First name": name_guess.split()[0] if name_guess else "",
		"Person - Last name": name_guess.split()[1] if name_guess else "",

		"Person - Email - Work": emails[0] if emails else "",
		"Person - Email - Home": "",
		"Person - Email - Other": emails[1] if len(emails) > 1 else "",

		"Person - ReferralURL": contact_link if contact_link else website,

		"Person - Phone - Work": phones[0] if phones else "",
		"Person - Phone - Home": "",
		"Person - Phone - Mobile": "",
		"Person - Phone - Other": phones[1] if len(phones) > 1 else "",

		"Person - DirectPhone": "",

		"Person - Website": website,

		"Person - Title": title,

		"Person - State": state,

		"Person - Role": "",

		"Person - Organization": org_name,
		"Person - LinkedInCompany": "",
		"Person - Employees": "",
		"Person - CompanyName": org_name,

		"Person - City": city,

		"Person - Name": name_guess,

		"Person - Sweet Spot": "",
		"Person - Sales Process Stage": "",
		"Person - Sample Modules": "",

		"Person - Person created": datetime.utcnow().isoformat()
	}

	return row


def save_to_csv(row, filename):

	df = pd.DataFrame([row])

	try:
		existing = pd.read_csv(filename)
		df = pd.concat([existing, df], ignore_index=True)

	except:
		pass

	df.to_csv(filename, index=False)


def main():

	org_name = input("Organization Name: ").strip()
	website = input("Website URL: ").strip()

	row = build_lead(org_name, website)

	if row:
		save_to_csv(row, "generated_leads.csv")
		print("Lead added to CSV")
	else:
		print("Failed to build lead")


if __name__ == "__main__":
	main()