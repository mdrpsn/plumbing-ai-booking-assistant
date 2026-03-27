def normalize_phone(phone: str) -> str:
    digits = "".join(character for character in phone if character.isdigit())
    if len(digits) == 10:
        digits = f"1{digits}"
    return f"+{digits}"
