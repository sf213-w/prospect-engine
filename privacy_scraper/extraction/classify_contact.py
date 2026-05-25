def classify_contact(email, snippet):
	email_lower = email.lower()
	snippet_lower = snippet.lower()

	if "privacy" in email_lower:
		return "generic_privacy_mailbox"

	if "compliance" in email_lower:
		return "compliance_team"

	if "hipaa" in snippet_lower:
		return "hipaa_contact"

	return "unknown"