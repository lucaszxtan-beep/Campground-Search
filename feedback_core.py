import json
import threading
from datetime import datetime, timezone
from pathlib import Path


FEEDBACK_FILE = (
    Path(__file__).resolve().parent
    / "feedback_data.json"
)

feedback_lock = threading.Lock()


def empty_feedback():
    return {}


def load_feedback():
    if not FEEDBACK_FILE.exists():
        return empty_feedback()

    try:
        with FEEDBACK_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        return data if isinstance(data, dict) else {}
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return {}


def save_feedback(data):
    temporary_file = FEEDBACK_FILE.with_suffix(
        ".json.tmp"
    )

    with temporary_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary_file.replace(FEEDBACK_FILE)


def add_feedback(campground, vote):
    if vote not in {"up", "down"}:
        raise ValueError(
            "Vote must be 'up' or 'down'."
        )

    campground_id = str(campground["id"])

    with feedback_lock:
        data = load_feedback()

        record = data.setdefault(
            campground_id,
            {
                "name": campground["name"],
                "thumbs_up": 0,
                "thumbs_down": 0,
                "history": [],
            },
        )

        record["name"] = campground["name"]

        if vote == "up":
            record["thumbs_up"] = (
                int(record.get("thumbs_up", 0)) + 1
            )
        else:
            record["thumbs_down"] = (
                int(record.get("thumbs_down", 0)) + 1
            )

        record.setdefault("history", []).append(
            {
                "vote": vote,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
        )

        save_feedback(data)


def get_feedback_summary(campground):
    campground_id = str(campground["id"])

    with feedback_lock:
        data = load_feedback()

    record = data.get(campground_id, {})

    thumbs_up = int(
        record.get("thumbs_up", 0)
    )

    thumbs_down = int(
        record.get("thumbs_down", 0)
    )

    total = thumbs_up + thumbs_down

    positive_percentage = (
        round(thumbs_up / total * 100, 1)
        if total
        else None
    )

    return {
        "thumbs_up": thumbs_up,
        "thumbs_down": thumbs_down,
        "total": total,
        "percent_positive": positive_percentage,
    }