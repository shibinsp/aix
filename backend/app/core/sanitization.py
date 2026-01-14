"""Input sanitization utilities."""
import re
from typing import Optional


def sanitize_user_input(text: str, max_length: int = 10000) -> str:
    """Sanitize user input to prevent prompt injection and other attacks."""
    if not text:
        return ""
    
    # Truncate to max length
    text = text[:max_length]
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Remove control characters except newlines and tabs
    text = ''.join(char for char in text if char == '\n' or char == '\t' or not (0 <= ord(char) < 32))
    
    return text.strip()


def sanitize_for_prompt(text: str) -> str:
    """Additional sanitization for text going into AI prompts."""
    text = sanitize_user_input(text)
    
    # Escape potential prompt injection patterns
    # Wrap user content in clear delimiters
    patterns_to_escape = [
        (r'```', '` ` `'),  # Break code blocks
        (r'<\|', '< |'),    # Break special tokens
        (r'\|>', '| >'),
    ]
    
    for pattern, replacement in patterns_to_escape:
        text = re.sub(pattern, replacement, text)
    
    return text


def validate_pagination(skip: int, limit: int, max_limit: int = 100) -> tuple[int, int]:
    """Validate and constrain pagination parameters."""
    skip = max(0, skip)
    limit = max(1, min(limit, max_limit))
    return skip, limit
