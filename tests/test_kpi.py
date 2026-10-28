from __future__ import annotations

import math

import pandas as pd
import pytest

import agents.kpi as kpi_agent


@pytest.fixture
def sales_tables():
    facts = pd.DataFrame(
        [
            # Janvier : deux lignes pour une commande, dont une en promotion.
            ("2024-01-02", 50, 100, 60, 2, "A", 2, 1),
            ("2024-01-02", 200, 200, 100, 1, "A", 4, 2),
            # Février : une commande, sans promotion.
            ("2024-02-03", 100, 300, 180, 3, "B", 5, 1),
            # Mars : deux commandes.
            ("2024-03-04", 100, 200, 100, 2, "C", 3, 2),
            ("2024-03-05", 100, 400, 200, 4, "D", 7, 1),
        ],
        columns=["OrderDate", "UnitPrice", "SalesAmount", "TotalProductCost", "OrderQuantity",
                 "SalesOrderNumber", "ShippingDays", "PromotionKey"],
    )
    dates = pd.DataFrame(
        [(f"2024-{month:02d}-{day:02d}", f"2024-{month:02d}")
         for month, day in [(1, 2), (2, 3), (3, 4), (3, 5)]],
        columns=["Date", "AnneeMois"],
    )
    return {"FactSales": facts, "DimDate": dates}


def test_kpi_aggregations_match_hand_calculated_reference(sales_tables, tmp_path, monkeypatch):
    monkeypatch.setattr(kpi_agent, "OUTPUT_DIR", tmp_path)

    result = kpi_agent.kpi({"tables": sales_tables})["kpi"].set_index("AnneeMois")

    jan = result.loc["2024-01"]
    assert jan["CA"] == pytest.approx(300)
    assert jan["Cout"] == pytest.approx(160)
    assert jan["Marge"] == pytest.approx(140)
    assert jan["MargePct"] == pytest.approx(140 / 300, abs=1e-4)
    assert jan["Quantite"] == 3
    assert jan["NbCommandes"] == 1
    assert jan["PanierMoyen"] == pytest.approx(300)
    assert jan["PartPromo"] == pytest.approx(200 / 300, abs=1e-4)
    assert jan["DelaiLivraison"] == pytest.approx(3)
    assert math.isnan(jan["EvolutionCA"])

    feb = result.loc["2024-02"]
    mar = result.loc["2024-03"]
    assert feb["EvolutionCA"] == pytest.approx(0)
    assert mar["CA"] == pytest.approx(600)
    assert mar["Marge"] == pytest.approx(300)
    assert mar["NbCommandes"] == 2
    assert mar["EvolutionCA"] == pytest.approx(1)


def test_kpi_does_not_calculate_evolution_across_missing_month(sales_tables, tmp_path, monkeypatch):
    facts = sales_tables["FactSales"].query("OrderDate != '2024-02-03'").copy()
    dates = sales_tables["DimDate"].query("AnneeMois != '2024-02'").copy()
    monkeypatch.setattr(kpi_agent, "OUTPUT_DIR", tmp_path)

    result = kpi_agent.kpi({"tables": {"FactSales": facts, "DimDate": dates}})["kpi"]

    march = result.set_index("AnneeMois").loc["2024-03"]
    assert math.isnan(march["EvolutionCA"])


def test_kpi_requires_fact_and_date_tables():
    with pytest.raises(KeyError, match="FactSales et DimDate"):
        kpi_agent.kpi({"tables": {}})
