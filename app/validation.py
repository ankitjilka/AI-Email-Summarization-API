import re
from datetime import datetime
from dateutil import parser as date_parser

from app.schemas import Summary


RELATIVE_DEADLINES = {
    "today",
    "tomorrow",
    "soon",
    "shortly",
    "as soon as possible",
    "asap",
}


def extract_explicit_dates(text: str) -> list[str]:
    """
    Extract explicit calendar dates from email body text.

    Does NOT treat words such as today/tomorrow as absolute dates.
    """

    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",
        r"\b(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|Nov|November|Dec|December)\s+\d{1,2},\s+\d{4}\b",
        r"\b\d{1,2}\s+(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|Nov|November|Dec|December)\s+\d{4}\b",
    ]

    matches = []

    for pattern in patterns:
        matches.extend(
            re.findall(pattern, text, flags=re.IGNORECASE)
        )

    normalized = []

    for value in matches:
        try:
            parsed = date_parser.parse(
                value,
                dayfirst=False,
                fuzzy=False,
            )
            normalized.append(parsed.strftime("%Y-%m-%d"))
        except (ValueError, OverflowError):
            continue

    return list(dict.fromkeys(normalized))


def validate_summary(
    summary: Summary,
    email_bodies: list[str],
) -> Summary:
    """
    Apply deterministic rules after LLM generation.
    """

    source_text = "\n".join(email_bodies)

    explicit_dates = extract_explicit_dates(source_text)

    for item in summary.action_items:
        if item.deadline:
            deadline = item.deadline.strip().lower()

            # Relative dates are not absolute calendar deadlines.
            if deadline in RELATIVE_DEADLINES:
                if deadline not in item.action.lower():
                    item.action = (
                        f"{item.action} "
                        f"(deadline mentioned as: {deadline})"
                    )

                item.deadline = None
                continue

            # Normalize an already valid date.
            try:
                parsed = date_parser.parse(
                    item.deadline,
                    dayfirst=False,
                    fuzzy=False,
                )
                normalized = parsed.strftime("%Y-%m-%d")

                if normalized in explicit_dates:
                    item.deadline = normalized
                else:
                    item.deadline = None

            except (ValueError, OverflowError):
                item.deadline = None

    return summary
