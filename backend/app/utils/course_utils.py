"""Utility functions for course management."""


def normalize_lesson_type(lesson_type: str) -> str:
    """Normalize AI-generated lesson types to valid enum values."""
    valid_types = {"text", "video", "interactive", "quiz", "lab"}
    lesson_type = lesson_type.lower().strip()

    # Map common AI variations to valid types
    type_mappings = {
        "lecture": "text",
        "reading": "text",
        "article": "text",
        "tutorial": "interactive",
        "hands-on": "interactive",
        "practice": "interactive",
        "exercise": "interactive",
        "assessment": "quiz",
        "test": "quiz",
        "exam": "quiz",
        "lab": "lab",
        "practical": "lab",
    }

    # Try exact match first
    if lesson_type in valid_types:
        return lesson_type

    # Try mapping
    if lesson_type in type_mappings:
        return type_mappings[lesson_type]

    # Default to text
    return "text"
