"""
Persistent storage — single JSON file.
All keys are lowercase and consistent throughout the app.
"""

import os
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "user_data.json")

# The single source of truth for the data schema
_DEFAULT_DATA: dict[str, Any] = {
    "plan": "",
    "goals": [],
    "history": {},
    "completed_topics": [],
    "courses": {},
}


def load_data() -> dict:
    """Load data from disk. Returns defaults if file missing or corrupted."""
    if not os.path.exists(FILE_PATH):
        return _DEFAULT_DATA.copy()

    try:
        with open(FILE_PATH, "r") as f:
            data = json.load(f)
        # Merge with defaults so new keys are always present
        return {**_DEFAULT_DATA, **data}
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load data: {e}. Returning defaults.")
        return _DEFAULT_DATA.copy()


def save_data(data: dict) -> None:
    """Save data to disk. Creates parent directories if needed."""
    os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)
    try:
        with open(FILE_PATH, "w") as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        logger.error(f"Failed to save data: {e}")
        raise


def log_progress(day: str, status: str) -> dict:
    """Record completion status for a given day. Returns updated data."""
    data = load_data()
    data["history"][day] = status
    save_data(data)
    return data


def save_course_summary(course_name: str, summary: str) -> None:
    """Persist a generated course summary."""
    data = load_data()
    data["courses"][course_name] = summary
    save_data(data)


def mark_topic_complete(topic: str) -> None:
    """Add a topic to the completed list (no duplicates)."""
    data = load_data()
    if topic not in data["completed_topics"]:
        data["completed_topics"].append(topic)
    save_data(data)
