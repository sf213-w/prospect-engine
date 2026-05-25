import re


EMAIL_RE = re.compile(
	r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)



def extract_emails(text):
	return list(set(EMAIL_RE.findall(text)))