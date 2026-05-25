import re



def normalize_phone(phone):
	digits = re.sub(r"\D", "", phone)

	if len(digits) == 10:
		return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

	return phone