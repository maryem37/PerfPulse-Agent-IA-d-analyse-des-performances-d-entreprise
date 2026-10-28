from __future__ import annotations

import numpy as np
import pandas as pd

from config import (
    OUTPUT_DIR, FENETRE_ZSCORE, SEUIL_ZSCORE,
    PLANCHER_STD, PERIODE_ANALYSE, MAX_ALERTES,
)

KPIS = ["CA", "Marge", "MargePct", "Quantite", "PanierMoyen", "PartPromo"]


def detect(state):
    k = state["kpi"].copy()
    debut, fin = PERIODE_ANALYSE
    k = k[(k["AnneeMois"] >= debut) & (k["AnneeMois"] <= fin)]

    # Calendrier complet : un mois manquant devient NaN (pas de décalage)
    mois = pd.period_range(debut, fin, freq="M").astype(str)
    k = k.set_index("AnneeMois").reindex(mois)
    k.index.name = "AnneeMois"

    alertes = []
    for kpi_nom in KPIS:
        s = k[kpi_nom]
        for i in range(FENETRE_ZSCORE, len(s)):
            val = s.iloc[i]
            ref = s.iloc[i - FENETRE_ZSCORE:i].dropna()
            if pd.isna(val) or len(ref) < FENETRE_ZSCORE // 2:
                continue

            moy = ref.mean()
            std = max(ref.std(ddof=0), PLANCHER_STD * abs(moy))
            if std == 0:
                continue
            z = (val - moy) / std

            # Écart avec le même mois de l'année précédente
            ecart_an = np.nan
            if i >= 12 and not pd.isna(s.iloc[i - 12]) and s.iloc[i - 12] != 0:
                ecart_an = (val - s.iloc[i - 12]) / abs(s.iloc[i - 12])

            if abs(z) < SEUIL_ZSCORE:
                continue

            alertes.append({
                "AnneeMois": s.index[i],
                "KPI": kpi_nom,
                "Valeur": round(float(val), 4),
                "Moyenne_ref": round(float(moy), 4),
                "ZScore": round(float(z), 2),
                "Ecart_pct": round(float((val - moy) / abs(moy)), 4) if moy else np.nan,
                "Ecart_annee_prec": round(float(ecart_an), 4) if not np.isnan(ecart_an) else np.nan,
                "Severite": "haute" if abs(z) >= 2 * SEUIL_ZSCORE else "moyenne",
            })

    df = pd.DataFrame(alertes)
    if df.empty:
        df = pd.DataFrame(columns=["AnneeMois", "KPI", "Valeur", "Moyenne_ref", "ZScore",
                                   "Ecart_pct", "Ecart_annee_prec", "Severite"])
    else:
        df["abs_z"] = df["ZScore"].abs()
        df = df.sort_values("abs_z", ascending=False).head(MAX_ALERTES).drop(columns="abs_z")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_DIR / "alertes.csv", index=False, encoding="utf-8")
    print(f"{len(df)} alertes détectées")
    return {"alertes": df.to_dict("records")}
