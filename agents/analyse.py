import numpy as np
import pandas as pd
from config import PROMO_SANS, FENETRE_ZSCORE

METRIQUE = {"CA": "CA", "Quantite": "Quantite", "Marge": "Marge", "MargePct": "Marge",
            "PanierMoyen": "CA", "PartPromo": "CA_Promo"}


def _prepare(tables):
    f = tables["FactSales"].copy()
    for c in ["SalesAmount", "TotalProductCost"]:
        f[c] = pd.to_numeric(f[c], errors="coerce")
    f["OrderDate"] = pd.to_datetime(f["OrderDate"])
    d = tables["DimDate"][["Date", "AnneeMois"]].copy()
    d["Date"] = pd.to_datetime(d["Date"])
    f = f.merge(d, left_on="OrderDate", right_on="Date", how="left")
    p = tables["DimProduct"][["ProductKey", "Category", "Subcategory", "ProductName"]]
    t = tables["DimSalesTerritory"][["SalesTerritoryKey", "SalesTerritoryRegion"]]
    f = f.merge(p, on="ProductKey", how="left").merge(t, on="SalesTerritoryKey", how="left")
    f["CA"] = f["SalesAmount"]
    f["Marge"] = f["SalesAmount"] - f["TotalProductCost"]
    f["Quantite"] = f["OrderQuantity"]
    f["EnPromo"] = f["PromotionKey"] != PROMO_SANS
    f["CA_Promo"] = np.where(f["EnPromo"], f["SalesAmount"], 0.0)
    return f


def _mois_ref(mois):
    p = pd.Period(mois, freq="M")
    return [str(p - i) for i in range(FENETRE_ZSCORE, 0, -1)]


def _agg(f, cle):
    return f.groupby(cle)[["CA", "Marge", "Quantite", "CA_Promo"]].sum()


def _pvm(cur, ref):
    cats = cur.index.union(ref.index)
    cur, ref = cur.reindex(cats).fillna(0), ref.reindex(cats).fillna(0)
    Q1, Q0 = cur["Quantite"].sum(), ref["Quantite"].sum()
    if Q0 == 0 or Q1 == 0:
        return None
    P1 = cur["CA"] / cur["Quantite"].replace(0, np.nan)
    P0 = (ref["CA"] / ref["Quantite"].replace(0, np.nan)).fillna(P1).fillna(0)
    s0 = ref["Quantite"] / Q0
    volume = ((Q1 * s0 - ref["Quantite"]) * P0).sum()
    mix = ((cur["Quantite"] - Q1 * s0) * P0).sum()
    prix = ((P1.fillna(0) - P0) * cur["Quantite"]).sum()
    ecart = cur["CA"].sum() - ref["CA"].sum()
    assert abs(volume + mix + prix - ecart) < 1.0, "PVM incohérent"
    return {"effet_volume": round(float(volume), 2), "effet_mix": round(float(mix), 2),
            "effet_prix": round(float(prix), 2), "ecart_CA_total": round(float(ecart), 2)}


def _top(cur, ref, metrique, n=3):
    idx = cur.index.union(ref.index)
    c, r = cur.reindex(idx).fillna(0), ref.reindex(idx).fillna(0)
    delta = (c[metrique] - r[metrique]).sort_values(key=abs, ascending=False).head(n)
    return [{"nom": str(nom),
             "valeur_mois": round(float(c.loc[nom, metrique]), 2),
             "valeur_reference": round(float(r.loc[nom, metrique]), 2),
             "ecart": round(float(delta[nom]), 2)} for nom in delta.index]


def analyse(state):
    f = _prepare(state["tables"])
    faits = []
    for a in state["alertes"]:
        a = {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in a.items()}
        mois, kpi = a["AnneeMois"], a["KPI"]
        refs = _mois_ref(mois)
        fm, fr = f[f["AnneeMois"] == mois], f[f["AnneeMois"].isin(refs)]
        n_ref = max(fr["AnneeMois"].nunique(), 1)
        met = METRIQUE[kpi]
        moy = lambda df: df / n_ref

        cat_m, cat_r = _agg(fm, "Category"), moy(_agg(fr, "Category"))
        reg_m, reg_r = _agg(fm, "SalesTerritoryRegion"), moy(_agg(fr, "SalesTerritoryRegion"))
        prod_m, prod_r = _agg(fm, "ProductName"), moy(_agg(fr, "ProductName"))

        ca_m = fm["CA"].sum()
        promo = {
            "part_promo_mois": round(float(fm["CA_Promo"].sum() / ca_m), 4) if ca_m else None,
            "part_promo_reference": round(float(fr["CA_Promo"].sum() / fr["CA"].sum()), 4)
                                    if fr["CA"].sum() else None,
            "marge_pct_lignes_promo": None, "marge_pct_lignes_hors_promo": None}
        for cle, masque in [("marge_pct_lignes_promo", fm["EnPromo"]),
                            ("marge_pct_lignes_hors_promo", ~fm["EnPromo"])]:
            sub = fm[masque]
            if sub["CA"].sum():
                promo[cle] = round(float(sub["Marge"].sum() / sub["CA"].sum()), 4)

        perte = fm[fm["Marge"] < 0]
        faits.append({
            "alerte": a,
            "periode_reference": f"{refs[0]} à {refs[-1]}",
            "metrique_analysee": met,
            "decomposition_CA_prix_volume_mix": _pvm(cat_m, cat_r),
            "top_categories": _top(cat_m, cat_r, met),
            "top_regions": _top(reg_m, reg_r, met),
            "top_produits": _top(prod_m, prod_r, met),
            "promotions": promo,
            "lignes_a_marge_negative": {
                "nombre": int(len(perte)),
                "perte_totale": round(float(perte["Marge"].sum()), 2),
                "part_des_lignes": round(len(perte) / len(fm), 4) if len(fm) else None},
        })
    return {"faits": faits}