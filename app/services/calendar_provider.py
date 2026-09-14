from datetime import datetime, timedelta, timezone

# Hour offsets from "now" per urgency tier - emergency gets same/next-day slots,
# standard a couple days out, review pushed furthest. Computed relative to the
# real current time instead of hardcoded dates, which go stale (and look
# broken in a demo) the moment the calendar rolls past them.
MOCK_SLOT_OFFSETS_HOURS = {
    "emergency": [4, 6, 9],
    "standard": [28, 32, 50],
    "review": [76, 100, 124],
}


def get_mock_availability(urgency: str) -> list[str]:
    offsets = MOCK_SLOT_OFFSETS_HOURS.get(urgency, MOCK_SLOT_OFFSETS_HOURS["review"])
    now = datetime.now(timezone.utc)
    return [
        (now + timedelta(hours=h)).strftime("%Y-%m-%dT%H:00:00Z") for h in offsets
    ]
