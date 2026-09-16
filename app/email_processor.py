import re
from html import unescape


def html_to_text(text: str) -> str:
    """
    Basic HTML-to-text conversion.
    Keeps this dependency-free for the demo.
    """
    if not text:
        return ""

    text = unescape(text)

    # Remove script/style blocks.
    text = re.sub(
        r"<(script|style).*?>.*?</\1>",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Convert common block tags to line breaks.
    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"</(p|div|li|tr|h[1-6])>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    # Remove remaining HTML tags.
    text = re.sub(r"<[^>]+>", "", text)

    return text


def remove_quoted_replies(text: str) -> str:
    """
    Remove common quoted-reply sections found in email bodies.
    This is intentionally conservative for the demo.
    """
    patterns = [
        r"\nOn .+?wrote:\s*.*",
        r"\n-----Original Message-----.*",
        r"\nBegin forwarded message:.*",
        r"\nFrom:\s.*\nSent:\s.*\nTo:\s.*",
    ]

    cleaned = text

    for pattern in patterns:
        cleaned = re.split(
            pattern,
            cleaned,
            maxsplit=1,
            flags=re.IGNORECASE | re.DOTALL,
        )[0]

    # Remove common quoted lines.
    lines = []
    for line in cleaned.splitlines():
        if line.strip().startswith(">"):
            continue
        lines.append(line)

    return "\n".join(lines)


def remove_signature(text: str) -> str:
    """
    Remove only obvious signature blocks.
    Be conservative so meaningful email content is not deleted.
    """

    patterns = [
        r"\n--\s*\n.*\Z",
        r"\nSent from my (iPhone|iPad|Android).*\Z",
        r"\nSent from Mail for .*?\Z",
    ]

    cleaned = text

    for pattern in patterns:
        cleaned = re.sub(
            pattern,
            "",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        )

    return cleaned.strip()

def normalize_text(text: str) -> str:
    """
    Normalize whitespace without destroying paragraph structure.
    """
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_email_body(body: str) -> str:
    """
    Run all preprocessing steps.
    """
    body = html_to_text(body)
    body = remove_quoted_replies(body)
    body = remove_signature(body)
    body = normalize_text(body)

    return body
