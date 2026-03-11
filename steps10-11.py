import csv

INPUT_FILE = "lead_dataset_scored.csv"
OUTPUT_FILE = "lead_dataset_campaigns.csv"


class CampaignAssigner:

	def __init__(self):
		self.rows = []


	def run(self):

		rows = self.load_data()

		for row in rows:

			campaign = self.assign_campaign(row)

			row["Campaign"] = campaign

			self.rows.append(row)

		self.write_output()


	def load_data(self):

		with open(INPUT_FILE, newline="", encoding="utf-8") as f:

			reader = csv.DictReader(f)

			return list(reader)


	def assign_campaign(self, row):

		lead_type = row.get("Lead Type", "")
		org_type = row.get("Organization Type", "")

		### Healthcare providers
		if lead_type == "Healthcare Practice":
			return "HIPAA Training Outreach"

		### Universities
		if lead_type == "University":
			return "Clinical Training Outreach"

		### Software vendors
		if lead_type == "Software Partner" or org_type == "Healthcare Software":
			return "API Partnership Outreach"

		### Cybersecurity companies
		if lead_type == "Cybersecurity Partner" or org_type == "Cybersecurity Vendor":
			return "Cybersecurity Partnership Outreach"

		### Staffing companies
		if lead_type == "Staffing Partner":
			return "Healthcare Staffing Partnership Outreach"

		return "General Healthcare Outreach"


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

	engine = CampaignAssigner()
	engine.run()