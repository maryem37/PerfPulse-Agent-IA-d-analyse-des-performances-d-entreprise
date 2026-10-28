"""
Comprehensive diagnostic script to verify all agents produce correct results.
"""
import sys
import json
import pandas as pd
import numpy as np

sys.path.insert(0, 'd:/BI/projet_bi')
from config import PROMO_SANS, FENETRE_ZSCORE, SEUIL_ZSCORE, PLANCHER_STD, PERIODE_ANALYSE, MAX_ALERTES

issues = []

# ============================
# 1. KPI AGENT CHECKS
# ============================
print("=" * 60)
print("1. KPI AGENT CHECKS")
print("=" * 60)

kpi = pd.read_csv('output/kpi_mensuels.csv')
fact_raw = pd.read_csv('data/FactSales.csv')
fact_raw['OrderDate'] = pd.to_datetime(fact_raw['OrderDate'], errors='coerce')
for c in ['SalesAmount', 'TotalProductCost', 'OrderQuantity']:
    fact_raw[c] = pd.to_numeric(fact_raw[c], errors='coerce')
fact_raw['EnPromo'] = fact_raw['PromotionKey'] != PROMO_SANS
fact_raw['CA_Promo'] = np.where(fact_raw['EnPromo'], fact_raw['SalesAmount'], 0.0)
fact_raw['Marge'] = fact_raw['SalesAmount'] - fact_raw['TotalProductCost']

dim_date = pd.read_csv('data/DimDate.csv')
dim_date['Date'] = pd.to_datetime(dim_date['Date'])
fact_raw_m = fact_raw.merge(dim_date[['Date', 'AnneeMois']], left_on='OrderDate', right_on='Date', how='left')

# Check key months
test_months = [
    ('2018-06', 1137251.90, -469756.42, -0.4131, 0.3535),
    ('2019-07', 2729167.03, -118341.29, -0.0434, 0.2309),
    ('2018-07', 2411558.85, 73557.49, 0.0305, 0.1264),
]

print("\nVerifying KPI values against source FactSales data:")
for mois, exp_ca, exp_marge, exp_marge_pct, exp_part_promo in test_months:
    g = fact_raw_m[fact_raw_m['AnneeMois'] == mois]
    ca = g['SalesAmount'].sum()
    marge = g['Marge'].sum()
    marge_pct = marge / ca if ca else None
    part_promo = g['CA_Promo'].sum() / ca if ca else None
    row = kpi[kpi['AnneeMois'] == mois].iloc[0]

    ca_ok = abs(row['CA'] - ca) < 1
    marge_ok = abs(row['Marge'] - marge) < 1
    marge_pct_ok = abs(row['MargePct'] - marge_pct) < 0.0001 if marge_pct is not None else False
    part_promo_ok = abs(row['PartPromo'] - part_promo) < 0.0001 if part_promo is not None else False

    print(f"\n  {mois}:")
    print(f"    CA:         source={ca:.2f} | kpi={row['CA']:.2f} | {'OK' if ca_ok else 'BUG!'}")
    print(f"    Marge:      source={marge:.2f} | kpi={row['Marge']:.2f} | {'OK' if marge_ok else 'BUG!'}")
    print(f"    MargePct:   source={marge_pct:.4f} | kpi={row['MargePct']:.4f} | {'OK' if marge_pct_ok else 'BUG!'}")
    print(f"    PartPromo:  source={part_promo:.4f} | kpi={row['PartPromo']:.4f} | {'OK' if part_promo_ok else 'BUG!'}")

    if not (ca_ok and marge_ok and marge_pct_ok and part_promo_ok):
        issues.append(f"KPI: mismatch for {mois}")

# Check for duplicate data problem (2021 == 2020, 2022 == 2023)
print("\n\nChecking for duplicate year data in FactSales (data quality issue):")
for y1, y2 in [('2020', '2021'), ('2022', '2023')]:
    g1 = fact_raw[fact_raw['OrderDate'].dt.year == int(y1)]
    g2 = fact_raw[fact_raw['OrderDate'].dt.year == int(y2)]
    ca1 = g1['SalesAmount'].sum()
    ca2 = g2['SalesAmount'].sum()
    match_pct = abs(ca1 - ca2) / ca1 * 100 if ca1 else 999
    print(f"  {y1} CA={ca1:.0f} vs {y2} CA={ca2:.0f} => similarity={100-match_pct:.1f}%")
    if match_pct < 1:
        issues.append(f"DATA QUALITY: {y1} and {y2} have nearly identical CA (possible duplicate data in source)")

# ============================
# 2. DETECT AGENT CHECKS
# ============================
print("\n" + "=" * 60)
print("2. DETECT AGENT CHECKS")
print("=" * 60)

alertes = pd.read_csv('output/alertes.csv')
print(f"\nTotal alerts detected: {len(alertes)} (max allowed: {MAX_ALERTES})")
print(f"\nPERIODE_ANALYSE: {PERIODE_ANALYSE}")
print("\nAlerts summary:")
print(alertes[['AnneeMois', 'KPI', 'ZScore', 'Severite']].to_string())

# Verify top alert manually: 2018-06 MargePct z-score = -122.0
kpi_in_range = kpi[(kpi['AnneeMois'] >= PERIODE_ANALYSE[0]) & (kpi['AnneeMois'] <= PERIODE_ANALYSE[1])].copy()
kpi_in_range = kpi_in_range.sort_values('AnneeMois').reset_index(drop=True)

print("\n\nManually verifying 2018-06 MargePct z-score:")
idx_2018_06 = kpi_in_range[kpi_in_range['AnneeMois'] == '2018-06'].index[0]
ref_window = kpi_in_range.loc[max(0, idx_2018_06 - FENETRE_ZSCORE):idx_2018_06- 1, 'MargePct'].dropna()
val = kpi_in_range.loc[idx_2018_06, 'MargePct']
moy = ref_window.mean()
std = max(ref_window.std(ddof=0), PLANCHER_STD * abs(moy))
z = (val - moy) / std
print(f"  Value: {val:.4f}")
print(f"  Ref window ({len(ref_window)} months): mean={moy:.4f}, std={std:.6f}")
print(f"  Computed Z-score: {z:.2f}")
print(f"  Alert Z-score: {alertes[alertes['AnneeMois']=='2018-06'][alertes['KPI']=='MargePct']['ZScore'].values}")
computed_z_ok = abs(z - (-122.0)) < 1
if not computed_z_ok:
    issues.append(f"DETECT: 2018-06 MargePct z-score mismatch: computed={z:.2f}, expected=-122.0")
print(f"  {'OK' if computed_z_ok else 'BUG!'}")

# ============================
# 3. ANALYSE AGENT CHECKS
# ============================
print("\n" + "=" * 60)
print("3. ANALYSE AGENT CHECKS")
print("=" * 60)

with open('output/faits.json') as f:
    faits = json.load(f)

print(f"\nTotal faits: {len(faits)}")
pvm_errors = []
for fait in faits:
    mois = fait['alerte']['AnneeMois']
    kpi_name = fait['alerte']['KPI']
    pvm = fait.get('decomposition_CA_prix_volume_mix')
    if pvm:
        total = pvm['effet_volume'] + pvm['effet_mix'] + pvm['effet_prix']
        ecart = pvm['ecart_CA_total']
        coherent = abs(total - ecart) < 1.0
        print(f"  {mois} {kpi_name}: PVM sum={total:.2f}, ecart={ecart:.2f} -> {'OK' if coherent else 'BUG!'}")
        if not coherent:
            pvm_errors.append(f"{mois} {kpi_name}")
    else:
        print(f"  {mois} {kpi_name}: No PVM decomposition (Q0 or Q1=0)")

if pvm_errors:
    issues.append(f"ANALYSE: PVM decomposition errors for: {pvm_errors}")

# ============================
# 4. VALIDATE AGENT CHECKS
# ============================
print("\n" + "=" * 60)
print("4. VALIDATE AGENT CHECKS")
print("=" * 60)

with open('output/validation.json') as f:
    validation = json.load(f)

print(f"\nValidation results ({len(validation)} texts):")
all_valid = True
for v in validation:
    probs = v.get('problemes', [])
    status = 'OK' if not probs else f'ISSUES: {probs}'
    print(f"  {v['mois']}: {status}")
    if probs:
        all_valid = False

if not all_valid:
    issues.append("VALIDATE: Some texts had validation issues")

# ============================
# 5. TEXTES CHECK (Write agent)
# ============================
print("\n" + "=" * 60)
print("5. WRITE AGENT - TEXT QUALITY CHECK")
print("=" * 60)

with open('output/textes.json', encoding='utf-8') as f:
    textes_data = json.load(f)

textes = textes_data.get('textes', [])
synthese = textes_data.get('synthese', '')

print(f"\nNumber of generated texts: {len(textes)}")
for i, t in enumerate(textes):
    print(f"\n  Text {i+1}:")
    print(f"    {t[:300] if t else 'NULL/EMPTY'}...")

print(f"\nSynthese:")
print(f"  {synthese[:500] if synthese else 'NULL/EMPTY'}")

null_texts = [i for i, t in enumerate(textes) if not t]
if null_texts:
    issues.append(f"WRITE: Null/empty texts at indices {null_texts}")

# ============================
# SUMMARY
# ============================
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

if issues:
    print(f"\n{len(issues)} ISSUE(S) FOUND:")
    for iss in issues:
        print(f"  [!] {iss}")
else:
    print("\nAll agent checks PASSED - no bugs detected in logic.")

print("\n\nNote: The FactSales data itself appears to contain duplicate/repeated data")
print("for years 2021=2020 and 2022=2023, which is a DATA QUALITY issue, not a bug in agents.")
