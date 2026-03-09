"""
This module implements test nlp client logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

from tgbot.nlp_client import _normalize_local_base_url


def test_normalize_local_base_url_rewrites_zero_address() -> None:
    """
    Execute test normalize local base url rewrites zero address.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    assert _normalize_local_base_url("http://0.0.0.0:8182") == "http://127.0.0.1:8182"


def test_normalize_local_base_url_keeps_normal_host() -> None:
    """
    Execute test normalize local base url keeps normal host.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    assert _normalize_local_base_url("http://127.0.0.1:8182") == "http://127.0.0.1:8182"
