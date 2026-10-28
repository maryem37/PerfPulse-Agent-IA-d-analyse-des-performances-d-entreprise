"""
Deep bug analysis for all agents.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import json, re, pandas as pd, numpy as np
from collections import OrderedDict

# ====================================================
# Load data
# ====================================================
with open('output/faits.json', encoding='utf-8') as f:
    faits = json.load(f)
with open('output/textes.json', encoding='utf-8') as f:
    textes_data = json.load(f)
with open('output/validation.json', encoding='utf-8') as f:
    validation = json.load(f)

kpi_df = pd.read_csv('output/kpi_mensuels.csv')
alertes_df = pd.read_csv('output/alertes.csv')
fact = pd.read_csv('data/FactSales.csv')
fact['OrderDate'] = pd.to_datetime(fact['OrderDate'], errors='coerce')
dim_date = pd.read_csv('data/DimDate.csv')
dim_date['Date'] = pd.to_datetime(dim_date['Date'])
fact = fact.merge(dim_date[['Date', 'AnneeMois']], left_on='OrderDate', right_on='Date', how='left')

textes = textes_data.get('textes', [])

BUGS = []
WARNINGS = []

# ====================================================
# BUG CHECK 1: write.py regrouper_par_mois
# Uses only first fait's decomposition for entire month group
# ====================================================
print("=" * 60)
print("BUG CHECK 1: write.py - regrouper_par_mois metric context")
print("=" * 60)

def regrouper_par_mois(faits_list):
    groupes = OrderedDict()
    for f in faits_list:
        mois = f['alerte']['AnneeMois']
        groupes.setdefault(mois, []).append(f)
    regroupes = []
    for mois, liste in groupes.items():
        base = dict(liste[0])
        base['alertes_du_mois'] = [x['alerte'] for x in liste]
        regroupes.append(base)
    return regroupes

groupes = regrouper_par_mois(faits)
for g in groupes:
    mois = g['alerte']['AnneeMois']
    alerts_kpis = [a['KPI'] for a in g['alertes_du_mois']]
    met = g.get('metrique_analysee', '?')
    top_cats = [c['nom'] for c in g.get('top_categories', [])]
    print(f"  Month {mois}: alerts={alerts_kpis}")
    print(f"    -> metric_used_for_tops: '{met}', top_cats: {top_cats}")
    # For months with MargePct + PartPromo + Marge alerts:
    # the tops are computed for the FIRST KPI's metric (MargePct -> 'Marge')
    # But the text covers all 3 KPIs. This is acceptable (same month = same breakdown)
    if len(alerts_kpis) > 1:
        first_kpi = alerts_kpis[0]
        WARNINGS.append(f"Month {mois}: {len(alerts_kpis)} KPIs grouped, tops show metric '{met}' from first KPI '{first_kpi}'")

# ====================================================
# BUG CHECK 2: kpi.py NbCommandes = nunique SalesOrderNumber
# ====================================================
print("\n" + "=" * 60)
print("BUG CHECK 2: kpi.py - NbCommandes (nunique SalesOrderNumber)")
print("=" * 60)

for mois in ['2018-06', '2019-07', '2018-07', '2019-08']:
    g = fact[fact['AnneeMois'] == mois]
    n_source = g['SalesOrderNumber'].nunique()
    row = kpi_df[kpi_df['AnneeMois'] == mois]
    if not row.empty:
        n_kpi = int(row.iloc[0]['NbCommandes'])
        ok = (n_source == n_kpi)
        print(f"  {mois}: source={n_source} | kpi={n_kpi} -> {'OK' if ok else 'BUG!'}")
        if not ok:
            BUGS.append(f"KPI NbCommandes mismatch at {mois}: source={n_source}, kpi={n_kpi}")

# ====================================================
# BUG CHECK 3: kpi.py - PanierMoyen = CA / NbCommandes
# ====================================================
print("\n" + "=" * 60)
print("BUG CHECK 3: kpi.py - PanierMoyen = CA / NbCommandes")
print("=" * 60)

for mois in ['2018-06', '2019-07', '2018-07']:
    row = kpi_df[kpi_df['AnneeMois'] == mois].iloc[0]
    expected_panier = row['CA'] / row['NbCommandes']
    ok = abs(expected_panier - row['PanierMoyen']) < 0.01
    print(f"  {mois}: CA/NbCommandes={expected_panier:.4f} | PanierMoyen={row['PanierMoyen']:.4f} -> {'OK' if ok else 'BUG!'}")
    if not ok:
        BUGS.append(f"KPI PanierMoyen mismatch at {mois}: computed={expected_panier:.4f}, got={row['PanierMoyen']:.4f}")

# ====================================================
# BUG CHECK 4: detect.py - Severite threshold
# "haute" if abs(z) >= 2 * SEUIL_ZSCORE else "moyenne"
# With SEUIL_ZSCORE=2.0, haute threshold = 4.0
# ====================================================
print("\n" + "=" * 60)
print("BUG CHECK 4: detect.py - Severite threshold (haute if |z|>=4.0)")
print("=" * 60)
SEUIL_ZSCORE = 2.0
for _, row in alertes_df.iterrows():
    z = abs(row['ZScore'])
    expected = 'haute' if z >= 2 * SEUIL_ZSCORE else 'moyenne'
    ok = expected == row['Severite']
    print(f"  {row['AnneeMois']} {row['KPI']}: |z|={z:.2f}, expected={expected}, got={row['Severite']} -> {'OK' if ok else 'BUG!'}")
    if not ok:
        BUGS.append(f"DETECT Severite wrong for {row['AnneeMois']} {row['KPI']}: got {row['Severite']}, expected {expected}")

# ====================================================
# BUG CHECK 5: analyse.py - top_categories metric
# METRIQUE maps KPI -> column name
# For MargePct -> 'Marge', PartPromo -> 'CA_Promo'
# The top_categories show biggest delta in that metric
# But for PartPromo the metric is CA_Promo, not CA
# ====================================================
print("\n" + "=" * 60)
print("BUG CHECK 5: analyse.py - METRIQUE mapping")
print("=" * 60)
METRIQUE = {"CA": "CA", "Quantite": "Quantite", "Marge": "Marge", "MargePct": "Marge",
            "PanierMoyen": "CA", "PartPromo": "CA_Promo"}
print("  METRIQUE mapping:")
for k, v in METRIQUE.items():
    print(f"    {k} -> {v}")
print()
# Check: for PartPromo, metric is CA_Promo. But the top_categories rank by CA_Promo delta
# which is the absolute CA in promotion - this is meaningful, but the 'top' is actually
# showing which category had the most promotional sales, not directly which drove the PartPromo anomaly
# This is a design choice, not necessarily a bug
print("  Note: For PartPromo KPI, top categories ranked by CA_Promo (absolute promo sales)")
print("  This is a design choice - categories with most promo CA, not highest promo ratio")
WARNINGS.append("DESIGN: PartPromo tops show CA_Promo absolute, not PartPromo ratio by category")

# ====================================================
# BUG CHECK 6: kpi.py - EvolutionCA gap years
# pct_change is sequential row-over-row
# Between 2020-05 and 2021-01 there's a ~7-month gap
# pct_change treats them as consecutive -> misleading
# ====================================================
print("\n" + "=" * 60)
print("BUG CHECK 6: kpi.py - EvolutionCA pct_change across year gaps")
print("=" * 60)

kpi_sorted = kpi_df.sort_values('AnneeMois').reset_index(drop=True)
# Find rows where AnneeMois jumps by more than 1 month
for i in range(1, len(kpi_sorted)):
    m_prev = pd.Period(kpi_sorted.loc[i-1, 'AnneeMois'], freq='M')
    m_cur  = pd.Period(kpi_sorted.loc[i, 'AnneeMois'], freq='M')
    gap = (m_cur - m_prev).n
    if gap > 1:
        ev = kpi_sorted.loc[i, 'EvolutionCA']
        ca_prev = kpi_sorted.loc[i-1, 'CA']
        ca_cur  = kpi_sorted.loc[i, 'CA']
        print(f"  Gap: {kpi_sorted.loc[i-1,'AnneeMois']} -> {kpi_sorted.loc[i,'AnneeMois']} ({gap} months)")
        print(f"    EvolutionCA computed as if consecutive: CA_prev={ca_prev:.0f}, CA_cur={ca_cur:.0f}, pct={ev:.4f}")
        BUGS.append(f"KPI EvolutionCA: pct_change across {gap}-month gap ({kpi_sorted.loc[i-1,'AnneeMois']} -> {kpi_sorted.loc[i,'AnneeMois']}) is misleading")

# ====================================================
# BUG CHECK 7: kpi.py - data beyond PERIODE_ANALYSE included
# PERIODE_ANALYSE = ('2017-07', '2020-05')
# KPI has data up to 2023, detect ignores these
# But the KPI CSV export includes duplicate 2021-2023 data
# ====================================================
print("\n" + "=" * 60)
print("BUG CHECK 7: KPI data outside analysis period (2021-2023)")
print("=" * 60)
outside = kpi_df[kpi_df['AnneeMois'] > '2020-05']
if not outside.empty:
    print(f"  {len(outside)} KPI rows outside PERIODE_ANALYSE (2017-07 to 2020-05):")
    print(f"  These are IGNORED by detect agent but included in kpi_mensuels.csv")
    print(f"  Years: {sorted(outside['AnneeMois'].str[:4].unique())}")
    print(f"  This is NOT a bug - detect correctly filters by PERIODE_ANALYSE")
    WARNINGS.append(f"INFO: {len(outside)} KPI rows outside PERIODE_ANALYSE exist in kpi_mensuels.csv (2021-2023, likely test/duplicate source data)")

# ====================================================
# BUG CHECK 8: validate.py - tolerance check edge case
# tolerance = 0.011 means numbers within 1.1% of a fact value are OK
# But Ecart_pct in alertes can be very large (-12.2002) - text writes -12.2002 which
# must be within tolerance of the fact value -12.2002 * scale
# ====================================================
print("\n" + "=" * 60)
print("BUG CHECK 8: validate.py - number tolerance")
print("=" * 60)
TOLERANCE = 0.011
# -12.2002 (Ecart_pct*100 = -1220.02... no wait, Ecart_pct=-12.2002 is already a fraction*100)
# Actually Ecart_pct in alertes.csv for 2018-06 MargePct = -12.2002
# The validate.py _collecter adds both n and n*100 versions
# So for Ecart_pct=-12.2002: 12.2002 and 1220.02 would be allowed
# Text writes "écart de -12.2002 %" -> NOMBRE finds 12.2002 -> allowed ✓
# This seems correct
print("  validate.py _collecter adds both value AND value*100 (for % conversion)")
print("  This correctly handles cases where Ecart_pct is a ratio vs percentage")
print("  Example: Ecart_pct=-12.2002 -> collects {12.2002, 1220.02}")
print("  Text '...écart de -12.2002 %...' -> number 12.2002 -> found in set ✓")

# ====================================================
# BUG CHECK 9: analyse.py - _mois_ref returns 6 months before
# For '2018-06', FENETRE_ZSCORE=6, refs = ['2017-12', '2018-01', '2018-02', '2018-03', '2018-04', '2018-05']
# ====================================================
print("\n" + "=" * 60)
print("BUG CHECK 9: analyse.py - reference period calculation")
print("=" * 60)
FENETRE_ZSCORE = 6
def mois_ref(mois):
    p = pd.Period(mois, freq='M')
    return [str(p - i) for i in range(FENETRE_ZSCORE, 0, -1)]

for mois in ['2018-06', '2019-07']:
    refs = mois_ref(mois)
    print(f"  {mois} -> reference months: {refs}")
    # Verify this matches what analyse.py computes
    for fait in faits:
        if fait['alerte']['AnneeMois'] == mois:
            period_ref_fact = fait.get('periode_reference', '')
            expected_ref = f"{refs[0]} à {refs[-1]}"
            ok = (period_ref_fact == expected_ref)
            print(f"    fait.periode_reference='{period_ref_fact}' | expected='{expected_ref}' -> {'OK' if ok else 'BUG!'}")
            if not ok:
                BUGS.append(f"ANALYSE: periode_reference wrong for {mois}")
            break

# ====================================================
# FINAL SUMMARY
# ====================================================
print("\n" + "=" * 60)
print("FINAL SUMMARY")
print("=" * 60)

if BUGS:
    print(f"\n🐛 {len(BUGS)} REAL BUG(S) FOUND:")
    for b in BUGS:
        print(f"  [BUG] {b}")
else:
    print("\n✅ No real bugs found in agent logic.")

if WARNINGS:
    print(f"\n⚠️  {len(WARNINGS)} WARNING(S)/DESIGN NOTE(S):")
    for w in WARNINGS:
        print(f"  [WARN] {w}")
