import re


NAME_RE = re.compile(
	r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b"
)



def extract_names(text):
	matches = NAME_RE.findall(text)

	results = []

	for first, last in matches:
		results.append({
			"first_name": first,
			"last_name": last,
		})

	return results