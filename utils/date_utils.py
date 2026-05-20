"""Utility functions for parsing and filtering article dates."""
import re
from datetime import datetime, date


def parse_article_date(date_str):
    """
    Parse a date string from Vietnamese news sites into a date object.
    Supports ISO format and Vietnamese date formats.
    Returns None if parsing fails.
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # ISO format: 2022-10-09T09:10:45+07:00
    patterns = [
        r"(\d{4}-\d{2}-\d{2})",  # Extract YYYY-MM-DD from any ISO-like string
    ]
    for pat in patterns:
        m = re.search(pat, date_str)
        if m:
            try:
                return datetime.strptime(m.group(1), "%Y-%m-%d").date()
            except ValueError:
                continue

    # Vietnamese format: 9/10/2022 (d/m/Y)
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_str)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass

    return None


def is_date_in_range(article_date, date_from=None, date_to=None):
    """
    Check if article_date falls within [date_from, date_to].
    If article_date is None, returns True (no date = no filtering).
    date_from and date_to are date objects or None (unbounded).
    """
    if article_date is None:
        return True
    if date_from and article_date < date_from:
        return False
    if date_to and article_date > date_to:
        return False
    return True
