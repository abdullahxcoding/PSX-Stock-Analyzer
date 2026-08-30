"""Shared numeric text-parsing helpers for PSX Data Portal scrapers.

PSX Data Portal tables consistently use: comma thousands separators, "-" for
missing/halted values, and parenthesized negatives (e.g. "(56.08)" == -56.08).
"""


def parse_float(text: str) -> float | None:
    text = text.replace(",", "").strip()
    if not text or text == "-":
        return None

    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]

    try:
        value = float(text)
    except ValueError:
        return None

    return -value if negative else value


def parse_int(text: str) -> int | None:
    value = parse_float(text)
    return int(value) if value is not None else None
