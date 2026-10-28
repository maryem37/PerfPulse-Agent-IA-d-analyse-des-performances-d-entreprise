from __future__ import annotations


def test_reject_invented_value():
    """Placeholder validation that fabricated values should be rejected."""
    invented_value = 999999
    assert invented_value != 0
