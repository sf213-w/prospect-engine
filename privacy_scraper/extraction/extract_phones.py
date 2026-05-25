import re


PHONE_RE = re.compile(
	r"\(?\d{3}\)?[\s\-.]\d{3}[\s\-.]\d{4}"
)



def extract_phones(text):
	return list(set(PHONE_RE.findall(text)))