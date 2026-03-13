import requests
import csv
import re
import dns.resolver
import smtplib

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime, UTC
from collections import deque

INPUT_FILE = "test.csv"
OUTPUT_FILE = "lead_dataset.csv"

MAX_PAGES_TO_CRAWL = 30

FREE_EMAIL_DOMAINS = {
	"gmail.com","yahoo.com","hotmail.com","outlook.com","aol.com","protonmail.com"
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

				pages = self.crawl_site(website)

				all_emails = set()
				all_phones = set()
				all_names = set()

				page_title = ""
				contact_page = ""

				for page in pages:

					html = self.download_page(page)

					if not html:
						continue

					html = self.decode_obfuscated_emails(html)

					soup = BeautifulSoup(html, "html.parser")

					if not page_title and soup.title:
						page_title = soup.title.get_text(strip=True)

					emails = self.clean_emails(re.findall(EMAIL_REGEX, html))
					all_emails.update(emails)

					for link in soup.find_all("a", href=True):

						href = link["href"]

						if href.startswith("mailto:"):

							email = href.replace("mailto:", "").strip()
							all_emails.add(email)

					phones = re.findall(PHONE_REGEX, html)
					all_phones.update(phones)

					names = self.extract_names(soup)
					all_names.update(names)

					if "contact" in page.lower():
						contact_page = page

				if all_emails:

					best_email = self.choose_best_email(list(all_emails))
					row["Contact Role Guess"] = self.infer_role_from_email(best_email)

				else:

					best_email = self.generate_fallback_email(website)
					row["Contact Role Guess"] = "Guessed"

				row["Person - Email - Work"] = best_email

				mx_valid = self.verify_domain_mx(best_email)
				smtp_valid = False

				if mx_valid:
					smtp_valid = self.verify_email_smtp(best_email)

				row["MX Valid"] = mx_valid
				row["SMTP Valid"] = smtp_valid

				if smtp_valid:
					row["Email Verified"] = "Mailbox Valid"
				elif mx_valid:
					row["Email Verified"] = "Domain Valid"
				else:
					row["Email Verified"] = "Invalid"

				if all_phones:
					row["Person - Phone - Work"] = list(all_phones)[0]

				if all_names:
					row["Person - Name"] = list(all_names)[0]

				if contact_page:
					row["Person - ReferralURL"] = contact_page

				metadata = self.extract_metadata(page_title, website)
				enriched = self.enrich_data(best_email, metadata)

				row.update(metadata)
				row.update(enriched)

			except Exception as e:

				row["Error"] = str(e)

			self.rows.append(row)

		self.write_csv()

	# -----------------------------
	# LOAD CSV
	# -----------------------------

	def load_organizations(self):

		orgs = []

		with open(INPUT_FILE, newline="", encoding="utf-8") as f:

			reader = csv.DictReader(f)

			for row in reader:
				orgs.append(row)

		return orgs

	# -----------------------------
	# CRAWLER
	# -----------------------------

	def crawl_site(self, base):

		visited = set()
		queue = deque([base])
		domain = urlparse(base).netloc

		pages = []

		while queue and len(pages) < MAX_PAGES_TO_CRAWL:

			url = queue.popleft()

			if url in visited:
				continue

			visited.add(url)
			pages.append(url)

			html = self.download_page(url)

			if not html:
				continue

			soup = BeautifulSoup(html, "html.parser")

			for link in soup.find_all("a", href=True):

				href = link["href"]
				full = urljoin(base, href)
				parsed = urlparse(full)

				if parsed.netloc == domain:

					if full not in visited:
						queue.append(full)

		return pages

	# -----------------------------
	# DOWNLOAD PAGE
	# -----------------------------

	def download_page(self, url):

		try:

			r = requests.get(url, headers=HEADERS, timeout=10)

			if r.status_code != 200:
				return None

			return r.text

		except Exception:
			return None

	# -----------------------------
	# DECODE HIDDEN EMAILS
	# -----------------------------

	def decode_obfuscated_emails(self, text):

		text = text.replace("[at]", "@").replace("(at)", "@")
		text = text.replace("[dot]", ".").replace("(dot)", ".")
		text = text.replace("&#64;", "@")

		return text

	# -----------------------------
	# EMAIL CLEANING
	# -----------------------------

	def clean_emails(self, emails):

		valid = []

		for e in emails:

			e = e.lower()

			if any(e.endswith(ext) for ext in [".png",".jpg",".jpeg",".svg",".gif",".webp"]):
				continue

			valid.append(e)

		return valid

	# -----------------------------
	# EMAIL PRIORITY
	# -----------------------------

	def choose_best_email(self, emails):

		priorities = {
			"training":100,
			"education":100,
			"learning":100,
			"compliance":100,
			"privacy":95,
			"security":90,
			"hr":90,
			"human":90,
			"director":80,
			"admin":75,
			"manager":70,
			"info":40,
			"contact":40
		}

		best_email = None
		best_score = -1

		for email in emails:

			score = 0
			local = email.split("@")[0]
			domain = email.split("@")[1]

			for key,value in priorities.items():

				if key in local:
					score += value

			if domain in FREE_EMAIL_DOMAINS:
				score -= 50

			if score > best_score:
				best_score = score
				best_email = email

		return best_email

	# -----------------------------
	# EMAIL VERIFICATION
	# -----------------------------

	def verify_domain_mx(self, email):

		try:

			domain = email.split("@")[1]

			records = dns.resolver.resolve(domain, "MX")

			return len(records) > 0

		except Exception:

			return False

	def verify_email_smtp(self, email):

		try:

			domain = email.split("@")[1]

			mx_records = dns.resolver.resolve(domain, "MX")
			mx_host = str(mx_records[0].exchange)

			server = smtplib.SMTP(timeout=10)

			server.connect(mx_host)
			server.helo("example.com")
			server.mail("verify@example.com")

			code, message = server.rcpt(email)

			server.quit()

			return code == 250

		except Exception:

			return False

	# -----------------------------
	# ROLE INFERENCE
	# -----------------------------

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

	# -----------------------------
	# NAME EXTRACTION
	# -----------------------------

	def extract_names(self, soup):

		names = []

		for tag in soup.find_all(["h1","h2","h3","p"]):

			text = tag.get_text(strip=True)

			if re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+$", text):
				names.append(text)

		return names

	# -----------------------------
	# METADATA
	# -----------------------------

	def extract_metadata(self, title, website):

		return {
			"Page Title": title,
			"Website Domain": urlparse(website).netloc
		}

	# -----------------------------
	# FALLBACK EMAIL
	# -----------------------------

	def generate_fallback_email(self, website):

		domain = urlparse(website).netloc

		return f"training@{domain}"

	# -----------------------------
	# ENRICHMENT
	# -----------------------------

	def enrich_data(self, email, metadata):

		data = {}

		if email:

			domain = email.split("@")[1]

			data["Email Domain"] = domain
			data["Free Email"] = domain in FREE_EMAIL_DOMAINS
			data["Company Domain"] = domain

		data["Country"] = "USA"
		data["US Status"] = "US"

		return data

	# -----------------------------
	# CSV OUTPUT
	# -----------------------------

	def write_csv(self):

		fieldnames = [
			"Person - Organization",
			"Person - CompanyName",
			"Person - Website",
			"Person - Person created",
			"Person - Email - Work",
			"Email Verified",
			"MX Valid",
			"SMTP Valid",
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

		with open(OUTPUT_FILE,"w",newline="",encoding="utf-8") as f:

			writer = csv.DictWriter(f,fieldnames=fieldnames)

			writer.writeheader()

			for r in self.rows:
				writer.writerow(r)


if __name__ == "__main__":

	engine = ProspectingEngine()
	engine.run()