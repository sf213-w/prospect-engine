def normalize_email(email):
	if not email:
		return ""

	email = email.strip().lower()
	email = email.replace("mailto:", "")
	email = email.rstrip(".,;:")

	return email