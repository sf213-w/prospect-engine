import requests
import csv
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime, UTC

INPUT_FILE = "test.csv"
OUTPUT_FILE = "lead_dataset.csv"

FREE_EMAIL_DOMAINS = {
	"gmail.com",
	"yahoo.com",
	"hotmail.com",
	"outlook.com",
	"aol.com",
	"protonmail.com"
}

EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
PHONE_REGEX = r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"

HEADERS = {
	"User-Agent": "Mozilla/5.0",
	"Accept-Language": "en-US,en;q=0.9"
}


class ProspectingEngine:

	def __init__(self):
		self.rows = []


	def run(self):

		orgs = self.load_organizations()

		for org in orgs:

			row = {}

			row["Person - Organization"] = org["Person - Organization"]
			row["Person - CompanyName"] = org["Person - Organization"]
			row["Person - Website"] = org["Person - Website"]
			row["Person - Person created"] = datetime.now(UTC).isoformat()

			website = org["Person - Website"]

			try:

				pages = self.build_page_list(website)

				all_emails = set()
				all_phones = set()
				all_names = set()

				page_title = ""
				contact_page = ""

				for page in pages:

					html = self.download_page(page)

					if not html:
						continue

					soup = BeautifulSoup(html, "html.parser")

					if not page_title and soup.title:
						page_title = soup.title.get_text(strip=True)

					emails = self.clean_emails(re.findall(EMAIL_REGEX, html))
					phones = re.findall(PHONE_REGEX, html)
					names = self.extract_names(soup)

					all_emails.update(emails)
					all_phones.update(phones)
					all_names.update(names)

					if "/contact" in page.lower():
						contact_page = page

				# Choose best email for outreach
				if all_emails:

					best_email = self.choose_best_email(list(all_emails))
					row["Person - Email - Work"] = best_email

					role = self.infer_role_from_email(best_email)
					row["Contact Role Guess"] = role

				if all_phones:
					row["Person - Phone - Work"] = list(all_phones)[0]

				if all_names:
					row["Person - Name"] = list(all_names)[0]

				if contact_page:
					row["Person - ReferralURL"] = contact_page

				metadata = self.extract_metadata(page_title, website)
				enriched = self.enrich_data(row.get("Person - Email - Work"), metadata)

				row.update(metadata)
				row.update(enriched)

			except Exception as e:

				row["Error"] = str(e)

			self.rows.append(row)

		self.write_csv()


	def load_organizations(self):

		orgs = []

		with open(INPUT_FILE, newline="", encoding="utf-8") as f:

			reader = csv.DictReader(f)

			for row in reader:
				orgs.append(row)

		return orgs


	def build_page_list(self, base):

		return [
			base,
			urljoin(base, "/contact"),
			urljoin(base, "/contact-us"),
			urljoin(base, "/about"),
			urljoin(base, "/team"),
			urljoin(base, "/staff"),
			urljoin(base, "/providers"),
			urljoin(base, "/leadership"),
			urljoin(base, "/education"),
			urljoin(base, "/training"),
			urljoin(base, "/compliance")
		]


	def download_page(self, url):

		try:

			r = requests.get(url, headers=HEADERS, timeout=10)

			if r.status_code != 200:
				return None

			return r.text

		except Exception:
			return None


	def clean_emails(self, emails):

		valid = []

		for e in emails:

			e = e.lower()

			if any(e.endswith(ext) for ext in [".png",".jpg",".jpeg",".svg",".gif",".webp"]):
				continue

			if "@" not in e:
				continue

			valid.append(e)

		return valid


	def choose_best_email(self, emails):

		priorities = {
			"training": 100,
			"education": 100,
			"learning": 100,
			"compliance": 100,
			"privacy": 95,
			"security": 90,
			"hr": 90,
			"humanresources": 90,
			"director": 80,
			"admin": 75,
			"administrator": 75,
			"manager": 70,
			"operations": 70,
			"info": 40,
			"contact": 40,
			"office": 40
		}

		best_email = None
		best_score = -1

		for email in emails:

			email = email.lower()

			score = 0

			local = email.split("@")[0]
			domain = email.split("@")[1]

			for key, value in priorities.items():

				if key in local:
					score += value

			if domain in FREE_EMAIL_DOMAINS:
				score -= 50

			if score > best_score:

				best_score = score
				best_email = email

		return best_email


	def infer_role_from_email(self, email):

		local = email.split("@")[0]

		if "training" in local or "education" in local:
			return "Training"

		if "compliance" in local or "privacy" in local:
			return "Compliance"

		if "security" in local:
			return "Security"

		if "hr" in local or "human" in local:
			return "HR"

		if "admin" in local or "manager" in local:
			return "Administration"

		return "General"


	def extract_names(self, soup):

		names = []

		for tag in soup.find_all(["h1","h2","h3","p"]):

			text = tag.get_text(strip=True)

			if re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+$", text):
				names.append(text)

		return names


	def extract_metadata(self, title, website):

		data = {}

		data["Page Title"] = title

		domain = urlparse(website).netloc

		data["Website Domain"] = domain

		return data


	def enrich_data(self, email, metadata):

		data = {}

		if email:

			domain = email.split("@")[1]

			data["Email Domain"] = domain
			data["Free Email"] = domain in FREE_EMAIL_DOMAINS
			data["Company Domain"] = domain

		website_domain = metadata.get("Website Domain")

		if website_domain:

			data["Country"] = "USA"
			data["US Status"] = "US"

		return data


	def write_csv(self):

		fieldnames = [
			"Person - Organization",
			"Person - CompanyName",
			"Person - Website",
			"Person - Person created",
			"Person - Email - Work",
			"Person - Phone - Work",
			"Person - ReferralURL",
			"Person - Name",
			"Contact Role Guess",
			"Page Title",
			"Website Domain",
			"Email Domain",
			"Free Email",
			"Company Domain",
			"Country",
			"US Status",
			"Error"
		]

		with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:

			writer = csv.DictWriter(f, fieldnames=fieldnames)

			writer.writeheader()

			for r in self.rows:
				writer.writerow(r)


if __name__ == "__main__":

	engine = ProspectingEngine()
	engine.run()