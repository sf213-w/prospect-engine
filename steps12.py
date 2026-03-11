import csv

INPUT_FILE = "lead_dataset_campaigns.csv"
OUTPUT_FILE = "lead_dataset_outreach_ready.csv"


LANDING_PAGES = {
	"HIPAA Training Outreach": "https://example.com/hipaa-training",
	"Clinical Training Outreach": "https://example.com/clinical-training",
	"API Partnership Outreach": "https://example.com/api-partnership",
	"Cybersecurity Partnership Outreach": "https://example.com/cybersecurity-partnership",
	"Healthcare Staffing Partnership Outreach": "https://example.com/staffing-partnership",
	"General Healthcare Outreach": "https://example.com/healthcare-solutions"
}


EMAIL_TEMPLATES = {

	"HIPAA Training Outreach": {
		"subject": "HIPAA Training Support for {organization}",
		"body": """Hello {name},

I came across {organization} while researching healthcare organizations focused on patient care and compliance.

We work with healthcare providers to deliver HIPAA-focused workforce training that helps organizations reduce compliance risk and keep staff up to date with regulatory requirements.

If helpful, you can review a brief overview here:
{landing_page}

If this is relevant for your team, I’d be happy to share more information.

Best regards
"""
	},

	"Clinical Training Outreach": {
		"subject": "Clinical training resources for {organization}",
		"body": """Hello {name},

I noticed {organization} while researching institutions involved in clinical education and healthcare training.

Our team works with universities and healthcare training programs to support workforce education and compliance training for clinical staff.

You can learn more here:
{landing_page}

If this is relevant for your program, I’d be happy to connect.

Best regards
"""
	},

	"API Partnership Outreach": {
		"subject": "Potential integration opportunity with {organization}",
		"body": """Hello {name},

I came across {organization} while researching healthcare technology platforms.

We work with healthcare software providers to integrate compliance and workforce training capabilities into their platforms via API.

Overview:
{landing_page}

If exploring integrations is relevant for your platform, I'd be glad to discuss further.

Best regards
"""
	},

	"Cybersecurity Partnership Outreach": {
		"subject": "Healthcare cybersecurity collaboration",
		"body": """Hello {name},

I came across {organization} while researching organizations working in healthcare cybersecurity.

We collaborate with cybersecurity vendors to support healthcare organizations with compliance and workforce security training.

Overview:
{landing_page}

If partnership opportunities are of interest, I would welcome a conversation.

Best regards
"""
	},

	"Healthcare Staffing Partnership Outreach": {
		"subject": "Training partnership with {organization}",
		"body": """Hello {name},

I came across {organization} while researching healthcare workforce providers.

We partner with staffing organizations to support workforce compliance and healthcare training programs.

More information:
{landing_page}

If a partnership could be useful for your organization, I’d be happy to connect.

Best regards
"""
	},

	"General Healthcare Outreach": {
		"subject": "Healthcare workforce training resources",
		"body": """Hello {name},

I came across {organization} while researching healthcare organizations.

Our team supports healthcare providers with compliance and workforce training resources.

You can learn more here:
{landing_page}

If this might be relevant for your team, I’d be happy to share additional information.

Best regards
"""
	}

}


class OutreachPreparer:

	def __init__(self):
		self.rows = []


	def run(self):

		rows = self.load_data()

		for row in rows:

			campaign = row.get("Campaign", "General Healthcare Outreach")

			landing_page = LANDING_PAGES.get(campaign)

			name = row.get("Person - Name", "there")
			org = row.get("Person - Organization", "")

			template = EMAIL_TEMPLATES.get(campaign)

			subject = template["subject"].format(
				name=name,
				organization=org
			)

			body = template["body"].format(
				name=name,
				organization=org,
				landing_page=landing_page
			)

			row["Landing Page"] = landing_page
			row["Email Subject"] = subject
			row["Email Body"] = body

			self.rows.append(row)

		self.write_output()


	def load_data(self):

		with open(INPUT_FILE, newline="", encoding="utf-8") as f:

			reader = csv.DictReader(f)
			return list(reader)


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

	engine = OutreachPreparer()
	engine.run()