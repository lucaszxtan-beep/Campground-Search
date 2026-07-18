from datetime import datetime, time


APP_VERSION = "v1.2-stable"


def to_datetime(date_value):
    """Convert a date object into a midnight datetime."""
    return datetime.combine(date_value, time.min)


def safe_int(value, default=0):
    """Convert a value to int without crashing."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default