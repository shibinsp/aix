"""Tests for input sanitization."""
import pytest
from app.core.sanitization import sanitize_user_input, sanitize_for_prompt, validate_pagination


def test_sanitize_removes_null_bytes():
    result = sanitize_user_input("hello\x00world")
    assert "\x00" not in result
    assert result == "helloworld"


def test_sanitize_truncates_long_input():
    long_input = "a" * 20000
    result = sanitize_user_input(long_input, max_length=100)
    assert len(result) == 100


def test_sanitize_removes_control_chars():
    result = sanitize_user_input("hello\x01\x02world")
    assert result == "helloworld"


def test_sanitize_preserves_newlines():
    result = sanitize_user_input("hello\nworld")
    assert result == "hello\nworld"


def test_sanitize_for_prompt_escapes_code_blocks():
    result = sanitize_for_prompt("```python\nprint('hi')\n```")
    assert "```" not in result


def test_validate_pagination_enforces_max():
    skip, limit = validate_pagination(0, 1000, max_limit=50)
    assert limit == 50


def test_validate_pagination_enforces_min():
    skip, limit = validate_pagination(-10, -5, max_limit=50)
    assert skip == 0
    assert limit == 1
