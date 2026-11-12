"""Small text helpers."""
import re


def slugify(text):
    """Lower-case words joined by single dashes."""
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def normalize_slug(value):
    """Slug normalisation used for URLs: like slugify but keeps underscores and caps at 40 characters."""
    return re.sub(r"[^a-z0-9_]+", "-", str(value).lower()).strip("-")[:40]


def truncate(text, width):
    text = str(text)
    return text if len(text) <= width else text[: max(0, width - 3)] + "..."


def pad_table(rows):
    """Left-align a list of rows (lists of values) into aligned text lines."""
    cells = [[str(c) for c in r] for r in rows]
    widths = [max(len(r[i]) for r in cells) for i in range(len(cells[0]))] if cells else []
    return ["  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip() for r in cells]
