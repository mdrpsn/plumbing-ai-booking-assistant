MOCK_SLOTS_BY_URGENCY = {
    "emergency": [
        "2026-03-27T09:00:00Z",
        "2026-03-27T11:00:00Z",
        "2026-03-27T14:00:00Z",
    ],
    "standard": [
        "2026-03-28T09:00:00Z",
        "2026-03-28T13:00:00Z",
        "2026-03-29T10:00:00Z",
    ],
    "review": [
        "2026-03-30T10:00:00Z",
        "2026-03-31T15:00:00Z",
        "2026-04-01T09:30:00Z",
    ],
}


def get_mock_availability(urgency: str) -> list[str]:
    return MOCK_SLOTS_BY_URGENCY.get(urgency, MOCK_SLOTS_BY_URGENCY["review"])
