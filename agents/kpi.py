from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
PROMO_SANS = 1  # PromotionKey 1 = "pas de promotion"


def kpi(state):
    tables = state.get("tables", {})
    if "FactSales" not in tables or "DimDate" not in tables:
        raise KeyError("Les tables FactSales et DimDate sont requises pour calculer les KPI.")

    f = tables["FactSales"].copy()
    d = tables["DimDate"][['Date', 'AnneeMois']].copy()

    for c in ["UnitPrice", "TotalProductCost", "SalesAmount"]:
        f[c] = pd.to_numeric(f[c], errors="coerce")
    f["OrderDate"] = pd.to_datetime(f["OrderDate"])
    d["Date"] = pd.to_datetime(d["Date"])

    f = f.merge(d, left_on="OrderDate", right_on="Date", how="left")
    f["EnPromo"] = f["PromotionKey"] != PROMO_SANS
    f["CA_Promo"] = np.where(f["EnPromo"], f["SalesAmount"], 0.0)

    g = f.groupby("AnneeMois").agg(
        CA=("SalesAmount", "sum"),
        Cout=("TotalProductCost", "sum"),
        Quantite=("OrderQuantity", "sum"),
        NbCommandes=("SalesOrderNumber", "nunique"),
        DelaiLivraison=("ShippingDays", "mean"),
        CA_Promo=("CA_Promo", "sum"),
    ).reset_index().sort_values("AnneeMois")

    g["Marge"] = g["CA"] - g["Cout"]
    g["MargePct"] = g["Marge"] / g["CA"]
    g["PanierMoyen"] = g["CA"] / g["NbCommandes"]
    g["PartPromo"] = g["CA_Promo"] / g["CA"]
    g["EvolutionCA"] = g["CA"].pct_change()
    g = g.drop(columns="CA_Promo").round(4)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "kpi_mensuels.csv"
    g.to_csv(output_file, index=False, encoding="utf-8")
    return {"kpi": g, "kpi_file": str(output_file)}