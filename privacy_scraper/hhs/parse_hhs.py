import csv
from collections import defaultdict


_COL_NAME = 0
_COL_ENTITY_TYPE = 2
_COL_BREACH_DATE = 4



def parse_hhs_csv(csv_path):
	providers = defaultdict(set)

	with open(csv_path, newline="", encoding="utf-8-sig") as f:
		reader = csv.reader(f)
		next(reader, None)

		for row in reader:
			if len(row) <= _COL_BREACH_DATE:
				continue

			name = row[_COL_NAME].strip()
			entity_type = row[_COL_ENTITY_TYPE].strip()
			breach_date = row[_COL_BREACH_DATE].strip()

			if "Healthcare Provider" not in entity_type:
				continue

			providers[name].add(breach_date)

	results = []

	for provider_name, breach_dates in providers.items():
		results.append({
			"provider_name": provider_name,
			"breach_submission_dates": sorted(list(breach_dates)),
		})

	return results