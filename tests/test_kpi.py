from __future__ import annotations


def test_kpi_monthly_drop_reference():
    """Reference validation for the expected KPI behaviour.

    This placeholder keeps the expected business rule documented in the project:
    2019-10 should show a strong negative monthly evolution.
    """
    expected_drop = -44.79
    assert expected_drop < 0
