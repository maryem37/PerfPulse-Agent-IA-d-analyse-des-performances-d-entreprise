from __future__ import annotations

import math

import pandas as pd
import pytest

import agents.kpi as kpi_agent


def test_evolution_is_calculated_only_for_adjacent_calendar_months(tmp_path, monkeypatch):
    monkeypatch.setattr(kpi_agent, "OUTPUT_DIR", tmp_path)
    sales = pd.DataFrame([
        ("2024-01-10", 10, 100, 60, 1, "A", 2, 1),
        ("2024-02-10", 10, 150, 80, 1, "B", 2, 1),
        ("2024-04-10", 10, 500, 300, 1, "C", 2, 1),
    ], columns=["OrderDate", "UnitPrice", "SalesAmount", "TotalProductCost",
                "OrderQuantity", "SalesOrderNumber", "ShippingDays", "PromotionKey"])
    dates = pd.DataFrame([
        ("2024-01-10", "2024-01"),
        ("2024-02-10", "2024-02"),
        ("2024-04-10", "2024-04"),
    ], columns=["Date", "AnneeMois"])

    result = kpi_agent.kpi({"tables": {"FactSales": sales, "DimDate": dates}})["kpi"]
    monthly = result.set_index("AnneeMois")

    assert monthly.loc["2024-02", "EvolutionCA"] == pytest.approx(0.5)
    assert math.isnan(monthly.loc["2024-04", "EvolutionCA"])
