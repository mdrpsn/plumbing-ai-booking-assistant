EMERGENCY_KEYWORDS = {
    "burst",
    "flood",
    "flooding",
    "gas leak",
    "leak ceiling",
    "overflow",
    "overflowing",
    "sewage",
    "no water",
    "water heater leaking",
}

STANDARD_KEYWORDS = {
    "clog",
    "clogged",
    "drain",
    "faucet",
    "garbage disposal",
    "leak",
    "running toilet",
    "toilet",
    "water heater",
}


def determine_urgency(issue: str) -> str:
    normalized = issue.strip().lower()

    if any(keyword in normalized for keyword in EMERGENCY_KEYWORDS):
        return "emergency"
    if any(keyword in normalized for keyword in STANDARD_KEYWORDS):
        return "standard"
    return "review"
