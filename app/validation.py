import re

from dateutil import parser as date_parser

from app.schemas import ActionItem, Summary


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
    Extract explicit calendar dates from email text and normalize
    them to YYYY-MM-DD.

    Relative terms such as today/tomorrow are not treated as dates.
    """

    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",
        (
            r"\b(?:Jan|January|Feb|February|Mar|March|Apr|April|May|"
            r"Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|"
            r"Nov|November|Dec|December)\s+\d{1,2},\s+\d{4}\b"
        ),
        (
            r"\b\d{1,2}\s+(?:Jan|January|Feb|February|Mar|March|Apr|"
            r"April|May|Jun|June|Jul|July|Aug|August|Sep|September|"
            r"Oct|October|Nov|November|Dec|December)\s+\d{4}\b"
        ),
    ]

    matches = []

    for pattern in patterns:
        matches.extend(
            re.findall(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
        )

    normalized = []

    for value in matches:
        try:
            parsed = date_parser.parse(
                value,
                dayfirst=False,
                fuzzy=False,
            )
            normalized.append(
                parsed.strftime("%Y-%m-%d")
            )
        except (ValueError, OverflowError):
            continue

    return list(dict.fromkeys(normalized))


def has_explicit_action_language(text: str) -> bool:
    """
    Detect whether the thread contains explicit request,
    assignment, or commitment language.

    This prevents purely informational emails from generating
    invented action items.
    """

    action_patterns = [
        r"\bplease\b",
        r"\bcan you\b",
        r"\bcould you\b",
        r"\bwould you\b",
        r"\byou should\b",
        r"\byou need to\b",
        r"\bwe need to\b",
        r"\bmust\b",
        r"\bi will\b",
        r"\bwe will\b",
        r"\bi'll\b",
        r"\bwe'll\b",
    ]

    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        for pattern in action_patterns
    )


def ensure_pending_delivery_action(
    summary: Summary,
    email_bodies: list[str],
) -> Summary:
    """
    Add a delivery/dispatch action only when the thread contains
    explicit future delivery/dispatch commitment language.

    Avoid treating generic words such as "shipment" or
    "replacement shipment" as proof that dispatch is still pending.
    """

    source_text = "\n".join(email_bodies).lower()

    future_delivery_patterns = [
        r"\bwill dispatch\b",
        r"\bwill be dispatched\b",
        r"\bwill deliver\b",
        r"\bwill be delivered\b",
        r"\bexpected dispatch date\b",
        r"\brevised dispatch date\b",
        r"\bexpected delivery date\b",
        r"\brevised expected delivery date\b",
        r"\bscheduled to dispatch\b",
        r"\bscheduled for delivery\b",
        r"\bplanned dispatch date\b",
        r"\bplanned delivery date\b",
    ]

    has_future_delivery_commitment = any(
        re.search(
            pattern,
            source_text,
            flags=re.IGNORECASE,
        )
        for pattern in future_delivery_patterns
    )

    if not has_future_delivery_commitment:
        return summary

    has_delivery_action = any(
        any(
            keyword in item.action.lower()
            for keyword in [
                "dispatch",
                "deliver",
                "delivery",
            ]
        )
        for item in summary.action_items
    )

    if has_delivery_action:
        return summary

    explicit_dates = extract_explicit_dates(
        "\n".join(email_bodies)
    )

    deadline = (
        explicit_dates[-1]
        if explicit_dates
        else None
    )

    summary.action_items.append(
        ActionItem(
            owner="Unspecified",
            action="Dispatch or deliver the order",
            status="pending",
            deadline=deadline,
        )
    )

    return summary

def validate_summary(
    summary: Summary,
    email_bodies: list[str],
) -> Summary:
    """
    Apply deterministic business rules after LLM generation.
    """

    source_text = "\n".join(email_bodies)

    # Purely informational threads should not contain
    # AI-invented action items.
    if not has_explicit_action_language(source_text):
        summary.action_items = []

    explicit_dates = extract_explicit_dates(source_text)

    for item in summary.action_items:
        if not item.deadline:
            continue

        deadline = item.deadline.strip().lower()

        # Relative terms are not absolute calendar dates.
        if deadline in RELATIVE_DEADLINES:
            if deadline not in item.action.lower():
                item.action = (
                    f"{item.action} "
                    f"(deadline mentioned as: {deadline})"
                )

            item.deadline = None
            continue

        # Normalize explicit date values.
        try:
            parsed = date_parser.parse(
                item.deadline,
                dayfirst=False,
                fuzzy=False,
            )

            normalized = parsed.strftime(
                "%Y-%m-%d"
            )

            if normalized in explicit_dates:
                item.deadline = normalized
            else:
                item.deadline = None

        except (ValueError, OverflowError):
            item.deadline = None

    # Ensure an obvious future delivery/dispatch action
    # isn't lost from the structured output.
    summary = ensure_pending_delivery_action(
        summary,
        email_bodies,
    )

    return summary
