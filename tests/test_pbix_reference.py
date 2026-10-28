"""Integration evaluation against the repository's local PBIX, when available."""
from __future__ import annotations

import pandas as pd
import pytest

import agents.kpi as kpi_agent
from config import PBIX_PATH


def test_all_monthly_kpis_reconcile_to_pbix_source(tmp_path, monkeypatch):
    if not PBIX_PATH.exists():
        pytest.skip("PBIX local absent : évaluation d'intégration ignorée")
    pbixray = pytest.importorskip("pbixray")
    model = pbixray.PBIXRay(str(PBIX_PATH))
    sales = model.get_table("FactSales")
    dates = model.get_table("DimDate")[["Date", "AnneeMois"]]
    monkeypatch.setattr(kpi_agent, "OUTPUT_DIR", tmp_path)

    actual = kpi_agent.kpi({"tables": {"FactSales": sales, "DimDate": dates}})["kpi"]

    # Oracle indépendant : agrégation directe des lignes source, sans réutiliser
    # les colonnes calculées ni le résultat CSV du pipeline.
    source = sales.copy()
    source["OrderDate"] = pd.to_datetime(source["OrderDate"])
    source["SalesAmount"] = pd.to_numeric(source["SalesAmount"], errors="coerce")
    source["TotalProductCost"] = pd.to_numeric(source["TotalProductCost"], errors="coerce")
    source = source.merge(dates.assign(Date=pd.to_datetime(dates["Date"])),
                          left_on="OrderDate", right_on="Date", how="left")
    assert source["AnneeMois"].notna().all(), "Certaines ventes n'ont pas de mois associé"
    expected = source.groupby("AnneeMois").agg(
        CA=("SalesAmount", "sum"),
        Cout=("TotalProductCost", "sum"),
        Quantite=("OrderQuantity", "sum"),
        NbCommandes=("SalesOrderNumber", "nunique"),
    ).sort_index()
    got = actual.set_index("AnneeMois").sort_index()

    assert list(got.index) == list(expected.index)
    for column in ["CA", "Cout", "Quantite", "NbCommandes"]:
        assert got[column].to_numpy() == pytest.approx(expected[column].to_numpy(), abs=1e-4)
    assert got["Marge"].to_numpy() == pytest.approx(
        (expected["CA"] - expected["Cout"]).to_numpy(), abs=1e-4
    )
    assert got["MargePct"].to_numpy() == pytest.approx(
        ((expected["CA"] - expected["Cout"]) / expected["CA"]).to_numpy(), abs=1e-4
    )
