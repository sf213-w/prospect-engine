import csv
import re

INPUT_FILE = "lead_dataset.csv"
OUTPUT_FILE = "lead_dataset_scored.csv"


HEALTHCARE_KEYWORDS = [
	"clinic",
	"medical",
	"health",
	"hospital",
	"physician",
	"care",
	"medicine"
]

UNIVERSITY_KEYWORDS = [
	"university",
	"college",
	"school of medicine"
]

STAFFING_KEYWORDS = [
	"staffing",
	"recruiting",
	"talent",
	"workforce"
]

SOFTWARE_KEYWORDS = [
	"software",
	"platform",
	"analytics",
	"saas"
]

CYBERSECURITY_KEYWORDS = [
	"cyber",
	"security",
	"infosec",
	"threat"
]


class LeadClassifier:

	def __init__(self):
		self.rows = []


	def run(self):

		rows = self.load_data()

		for row in rows:

			org_type = self.classify_organization(row)

			row["Organization Type"] = org_type

			score = self.score_lead(row, org_type)

			row["Lead Score"] = score

			row["Lead Type"] = self.determine_lead_type(org_type)

			self.rows.append(row)

		self.write_output()


	def load_data(self):

		with open(INPUT_FILE, newline="", encoding="utf-8") as f:

			reader = csv.DictReader(f)

			return list(reader)


	def classify_organization(self, row):

		text = " ".join([
			row.get("Person - Organization", ""),
			row.get("Page Title", ""),
			row.get("Website Domain", "")
		]).lower()


		if any(k in text for k in UNIVERSITY_KEYWORDS):
			return "University"

		if any(k in text for k in STAFFING_KEYWORDS):
			return "Staffing Company"

		if any(k in text for k in CYBERSECURITY_KEYWORDS):
			return "Cybersecurity Vendor"

		if any(k in text for k in SOFTWARE_KEYWORDS):
			return "Healthcare Software"

		if any(k in text for k in HEALTHCARE_KEYWORDS):
			return "Medical Practice"

		return "Other"


	def score_lead(self, row, org_type):

		score = 0

		### US organization
		if row.get("US Status") == "US":
			score += 20


		### Healthcare relevance
		if org_type in ["Medical Practice", "Hospital"]:
			score += 30


		### University
		if org_type == "University":
			score += 10


		### Non-free email
		free_email = row.get("Free Email")

		if free_email == "False" or free_email is False:
			score += 15


		### Compliance indicators
		text = (row.get("Page Title", "") + " " + row.get("Person - Organization", "")).lower()

		if any(k in text for k in ["hipaa","compliance","training","security"]):
			score += 25


		### Website present
		if row.get("Person - Website"):
			score += 10


		return score


	def determine_lead_type(self, org_type):

		if org_type in ["Medical Practice", "Hospital"]:
			return "Healthcare Practice"

		if org_type == "University":
			return "University"

		if org_type == "Healthcare Software":
			return "Software Partner"

		if org_type == "Cybersecurity Vendor":
			return "Cybersecurity Partner"

		if org_type == "Staffing Company":
			return "Staffing Partner"

		return "General"


	def write_output(self):

		if not self.rows:
			return


		fieldnames = list(self.rows[0].keys())


		with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:

			writer = csv.DictWriter(f, fieldnames=fieldnames)

			writer.writeheader()

			for r in self.rows:
				writer.writerow(r)


if __name__ == "__main__":

	engine = LeadClassifier()
	engine.run()