from __future__ import annotations

import csv
from html import escape
import io
import json
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"

# ──────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────

def _format_fr(v, decimals=2, signed=False):
    if v is None:
        return "—"
    try:
        number = float(v)
        if number != number or number in (float("inf"), float("-inf")):
            return "—"
        pattern = f"{{:{'+' if signed else ''},.{decimals}f}}"
        return pattern.format(number).replace(",", "\u202f").replace(".", ",")
    except (TypeError, ValueError):
        return str(v)


def _fmt(v, pct=False, decimals=2):
    """Format a number using French separators, optionally as a percentage."""
    if pct:
        try:
            return _format_fr(float(v) * 100, decimals, signed=True) + " %"
        except (TypeError, ValueError):
            return "—"
    return _format_fr(v, decimals)


def _sev_badge(sev):
    cls = "badge-haute" if sev == "haute" else "badge-moyenne"
    return f'<span class="badge {cls}">{sev}</span>'


def _regrouper(faits):
    """Regroupe les faits par mois (même logique que write.py)."""
    groupes = OrderedDict()
    for f in faits:
        mois = f["alerte"]["AnneeMois"]
        groupes.setdefault(mois, []).append(f)
    regroupes = []
    for mois, liste in groupes.items():
        base = dict(liste[0])
        base["alertes_du_mois"] = [x["alerte"] for x in liste]
        regroupes.append(base)
    return regroupes


# ──────────────────────────────────────────────────────────
# HTML builder
# ──────────────────────────────────────────────────────────

_CSS = """
:root {
  --bg:       #f8fafc;
  --surface:  #ffffff;
  --surface2: #e2e8f0;
  --border:   #cbd5e1;
  --accent:   #4f46e5;
  --accent2:  #0f766e;
  --danger:   #b91c1c;
  --warn:     #b45309;
  --text:     #0f172a;
  --muted:    #475569;
  --radius:   12px;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  padding: 0 0 60px;
}

/* ── Header ── */
header {
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 75%);
  border-bottom: 1px solid var(--border);
  padding: 40px 60px 36px;
  position: relative;
  overflow: hidden;
}
header::before {
  content: '';
  position: absolute; inset: 0;
  background: radial-gradient(ellipse at 70% 50%, rgba(108,99,255,.15) 0%, transparent 70%);
  pointer-events: none;
}
.header-inner { position: relative; z-index: 1; }
.logo { font-size: 13px; font-weight: 600; color: #c7d2fe; letter-spacing: 2px;
        text-transform: uppercase; margin-bottom: 12px; }
h1 { font-size: 32px; font-weight: 700; letter-spacing: -.5px; color: #ffffff; }
h1 span { color: #a5b4fc; }
.header-meta { margin-top: 10px; color: #cbd5e1; font-size: 13px; }
.header-meta strong { color: #ffffff; }

/* ── Layout ── */
.container { max-width: 1200px; margin: 0 auto; padding: 0 40px; }
section { margin-top: 48px; }
h2 {
  font-size: 20px; font-weight: 700; color: var(--text);
  border-left: 4px solid var(--accent); padding-left: 14px;
  margin-bottom: 20px;
}
h3 { font-size: 15px; font-weight: 600; color: var(--accent2); margin-bottom: 10px; }

/* ── Synthèse card ── */
.synthese-card {
  background: linear-gradient(135deg, #eef2ff, #ecfeff);
  border: 1px solid #c7d2fe;
  border-radius: var(--radius);
  padding: 28px 32px;
  font-size: 15px;
  color: var(--text);
  line-height: 1.8;
}
.reading-guide {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 22px 26px;
  color: var(--text);
}
.reading-guide ul { margin: 10px 0 0 20px; }
.reading-guide li { margin: 5px 0; color: var(--muted); }
.analysis-note {
  margin: 12px 0;
  padding: 10px 14px;
  border-left: 3px solid var(--warn);
  background: rgba(255,179,71,.08);
  color: var(--muted);
  font-size: 12px;
}

/* ── KPI grid ── */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 28px;
}
.kpi-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px 22px;
  transition: border-color .2s, transform .2s;
}
.kpi-card:hover { border-color: var(--accent); transform: translateY(-2px); }
.kpi-card .label { font-size: 11px; color: var(--muted); text-transform: uppercase;
                   letter-spacing: 1px; margin-bottom: 6px; }
.kpi-card .value { font-size: 26px; font-weight: 700; }
.kpi-card .value.pos { color: var(--accent2); }
.kpi-card .value.neg { color: var(--danger); }
.kpi-card .sub   { font-size: 12px; color: var(--muted); margin-top: 4px; }

/* ── Tables ── */
.table-wrap { overflow-x: auto; border-radius: var(--radius); border: 1px solid var(--border); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
thead tr { background: var(--surface2); }
th { padding: 12px 16px; text-align: left; color: var(--muted); font-weight: 600;
     font-size: 11px; text-transform: uppercase; letter-spacing: .8px;
     border-bottom: 1px solid var(--border); white-space: nowrap; }
td { padding: 11px 16px; border-bottom: 1px solid rgba(46,51,71,.6); vertical-align: top; }
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover td { background: rgba(108,99,255,.05); }
td.num { text-align: right; font-variant-numeric: tabular-nums; font-family: monospace; }
td.neg { color: var(--danger); }
td.pos { color: var(--accent2); }

/* ── Badges ── */
.badge {
  display: inline-block; padding: 2px 10px; border-radius: 20px;
  font-size: 11px; font-weight: 700; letter-spacing: .5px; text-transform: uppercase;
}
.badge-haute   { background: rgba(255,77,109,.2); color: var(--danger); border: 1px solid rgba(255,77,109,.4); }
.badge-moyenne { background: rgba(255,179,71,.2);  color: var(--warn);   border: 1px solid rgba(255,179,71,.4); }
.badge-ok      { background: rgba(0,212,170,.2);   color: var(--accent2); border: 1px solid rgba(0,212,170,.4); }

/* ── Alert month cards ── */
.month-cards { display: flex; flex-direction: column; gap: 24px; }
.month-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  transition: border-color .2s;
}
.month-card:hover { border-color: rgba(108,99,255,.5); }
.month-card-header {
  background: var(--surface2);
  padding: 16px 24px;
  display: flex; align-items: center; gap: 14px;
  border-bottom: 1px solid var(--border);
}
.month-label { font-size: 18px; font-weight: 700; }
.month-card-body { padding: 20px 24px; }
.month-text {
  font-size: 14px; line-height: 1.8; color: var(--text);
  background: #eef2ff;
  border-left: 3px solid var(--accent);
  padding: 14px 18px; border-radius: 0 8px 8px 0;
  margin-bottom: 20px;
  white-space: pre-wrap;
}
.two-col { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
@media (max-width: 700px) { .two-col { grid-template-columns: 1fr; } }
@media print {
  body { background: #fff; color: #000; padding: 0; }
  header { padding: 20px 28px; }
  .container { max-width: none; padding: 0 20px; }
  section { margin-top: 24px; }
  .month-card, .kpi-card, .reading-guide, .synthese-card { break-inside: avoid; box-shadow: none; }
  .table-wrap { overflow: visible; }
  a { color: inherit; text-decoration: none; }
}

/* ── Footer ── */
footer {
  margin-top: 60px; padding: 28px 60px;
  border-top: 1px solid var(--border);
  color: var(--muted); font-size: 12px;
  display: flex; justify-content: space-between; align-items: center;
}
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
       background: var(--accent2); margin-right: 6px; }
"""

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PerfPulse — Rapport BI {date}</title>
  <meta name="description" content="Rapport d'analyse des performances d'entreprise généré par PerfPulse Agent IA">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>{css}</style>
</head>
<body>

<header>
  <div class="header-inner">
    <div class="logo">PerfPulse · Agent IA</div>
    <h1>Rapport d'analyse <span>des performances</span></h1>
    <div class="header-meta">
      Généré le <strong>{date}</strong> &nbsp;·&nbsp;
      KPI disponibles : <strong>{periode}</strong> (<strong>{nb_kpi_mois}</strong> mois) &nbsp;·&nbsp;
      détection : <strong>{periode_detection}</strong> &nbsp;·&nbsp;
      <strong>{nb_alertes}</strong> alertes détectées ;
      elles concernent <strong>{nb_mois_alertes}</strong> mois
    </div>
  </div>
</header>

<div class="container">

  <!-- ── Synthèse ── -->
  <section>
    <h2>Synthèse générale</h2>
    <div class="synthese-card">{synthese}</div>
  </section>

  <section>
    <h2>Comment lire ce rapport</h2>
    <div class="reading-guide">{guide}</div>
  </section>

  <!-- ── KPI globaux ── -->
  <section>
    <h2>KPI globaux sur la période</h2>
    <div class="kpi-grid">{kpi_cards}</div>
  </section>

  <!-- ── Alertes globales ── -->
  <section>
    <h2>Tableau des anomalies détectées</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Mois</th><th>KPI</th><th>Valeur</th><th>Moyenne réf.</th>
            <th>Écart relatif (%)</th><th>Z-Score</th><th>Sévérité</th>
          </tr>
        </thead>
        <tbody>{alertes_rows}</tbody>
      </table>
    </div>
  </section>

  <!-- ── Analyse par mois ── -->
  <section>
    <h2>Analyse détaillée par mois</h2>
    <div class="month-cards">{month_cards}</div>
  </section>

  <!-- ── KPI mensuel ── -->
  <section>
    <h2>Évolution mensuelle des KPI</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Mois</th><th>CA (€)</th><th>Marge (€)</th><th>Taux de marge</th>
            <th>Quantité (unités)</th><th>Commandes distinctes</th><th>Panier moyen (€)</th>
            <th>CA en promotion</th><th>Évolution CA vs mois précédent</th>
          </tr>
        </thead>
        <tbody>{kpi_rows}</tbody>
      </table>
    </div>
  </section>

</div>

<footer>
  <div><span class="dot"></span>PerfPulse Agent IA &mdash; rapport automatique</div>
  <div>Généré le {date}</div>
</footer>

</body>
</html>"""


def _build_kpi_cards(kpi_df):
    """6 stat cards with aggregated totals over the analysis period."""
    ca_total   = kpi_df["CA"].sum()
    marge_tot  = kpi_df["Marge"].sum()
    marge_pct  = marge_tot / ca_total if ca_total else 0
    qtot       = int(kpi_df["Quantite"].sum())
    n_mois     = len(kpi_df)
    promo_moy  = kpi_df["PartPromo"].mean()
    nb_commandes = kpi_df["NbCommandes"].sum()
    panier_moy = ca_total / nb_commandes if nb_commandes else 0

    def card(label, value, sub="", neg=False, pos=False):
        cls = "neg" if neg else ("pos" if pos else "")
        return (f'<div class="kpi-card">'
                f'<div class="label">{label}</div>'
                f'<div class="value {cls}">{value}</div>'
                f'<div class="sub">{sub}</div>'
                f'</div>')

    pos_marge = marge_tot >= 0
    cards = [
        card("CA Total", f"{_format_fr(ca_total, 0)} €", f"sur {n_mois} mois", pos=True),
        card("Marge Totale", f"{_format_fr(marge_tot, 0)} €", f"{_format_fr(marge_pct*100, 1)} % du CA",
             neg=not pos_marge, pos=pos_marge),
        card("Taux de Marge Global", f"{_format_fr(marge_pct*100, 2)} %", "Marge totale / CA total",
             neg=not pos_marge, pos=pos_marge),
        card("Quantités Vendues", _format_fr(qtot, 0), "unités totales"),
        card("Part Promo Moy. Mensuelle", f"{_format_fr(promo_moy*100, 1)} %", "Moyenne simple des ratios mensuels"),
        card("Panier Moyen Global", f"{_format_fr(panier_moy, 0)} €", "CA total / commandes distinctes totales"),
    ]
    return "".join(cards)


def _build_alertes_rows(alertes):
    rows = []
    for a in alertes:
        is_ratio = a.get("KPI") in {"MargePct", "PartPromo"}
        ecart = a.get("Ecart_pct")
        ecart_str = _fmt(ecart, pct=True, decimals=2) if ecart is not None and ecart == ecart else "—"
        z = a.get("ZScore", 0)
        z_cls = "neg" if z < 0 else "pos"
        ecart_cls = "neg" if (ecart or 0) < 0 else "pos"
        rows.append(
            f'<tr>'
            f'<td><strong>{a["AnneeMois"]}</strong></td>'
            f'<td>{a["KPI"]}</td>'
            f'<td class="num">{_fmt(a.get("Valeur"), pct=is_ratio, decimals=2 if is_ratio else 4)}</td>'
            f'<td class="num">{_fmt(a.get("Moyenne_ref"), pct=is_ratio, decimals=2 if is_ratio else 4)}</td>'
            f'<td class="num {ecart_cls}">{ecart_str}</td>'
            f'<td class="num {z_cls}">{a.get("ZScore","—")}</td>'
            f'<td>{_sev_badge(a.get("Severite",""))}</td>'
            f'</tr>'
        )
    return "".join(rows)


def _build_month_cards(groupes, textes, validation):
    """One card per alert month with text, top categories, top regions."""
    val_map = {v["mois"]: v for v in (validation or [])}
    cards = []
    for i, (g, txt) in enumerate(zip(groupes, textes or [])):
        mois = g["alerte"]["AnneeMois"]
        v    = val_map.get(mois, {})
        pb   = v.get("problemes", [])
        gabarit = v.get("remplace_par_gabarit", False)

        # Alert badges
        badges = " ".join(_sev_badge(a.get("Severite", "")) for a in g["alertes_du_mois"])
        kpi_list = ", ".join(a["KPI"] for a in g["alertes_du_mois"])
        status_badge = ('<span class="badge badge-ok">validé</span>' if not pb
                        else '<span class="badge badge-haute">gabarit</span>')

        # Top categories table
        def mini_table(title, items, col_label, metric, unit):
            if not items:
                return ""
            rows_html = "".join(
                f'<tr><td>{escape(str(it["nom"]))}</td>'
                f'<td class="num {"neg" if it["ecart"]<0 else "pos"}">'
                f'{_format_fr(it["ecart"], 2, signed=True)} {unit}</td></tr>'
                for it in items
            )
            return (f'<h3>{title}</h3>'
                    f'<div class="table-wrap"><table>'
                    f'<thead><tr><th>{col_label}</th><th>Écart sur {escape(str(metric))}</th></tr></thead>'
                    f'<tbody>{rows_html}</tbody>'
                    f'</table></div>')

        metric = g.get("metrique_analysee", "KPI")
        unit = "unités" if metric == "Quantite" else "€"
        cats = mini_table("Catégories avec le plus grand écart", g.get("top_categories", []), "Catégorie", metric, unit)
        regs = mini_table("Régions avec le plus grand écart", g.get("top_regions", []), "Région", metric, unit)
        products = mini_table("Produits avec le plus grand écart", g.get("top_produits", []), "Produit", metric, unit)

        # Promo info
        promo = g.get("promotions", {})
        pp = promo.get("part_promo_mois")
        promo_info = f"Part promo : <strong>{_format_fr(pp*100, 1)} %</strong>" if pp is not None else ""

        # Marge négative
        mn = g.get("lignes_a_marge_negative", {})
        mn_nb = mn.get("nombre", 0)
        mn_loss = mn.get("perte_totale", 0)
        marge_neg_info = (f"Lignes à marge négative : <strong>{mn_nb}</strong> "
                          f"(perte : <span style='color:var(--danger)'>{_format_fr(mn_loss, 0)} €</span>)"
                          if mn_nb else "")

        txt_display = escape(txt).replace("\n", "<br>") if txt else "<em style='color:var(--muted)'>Texte non disponible.</em>"
        metric_labels = {"CA": "CA (€)", "Marge": "marge (€)", "Quantite": "quantité (unités)", "CA_Promo": "CA promotionnel (€)"}
        dimension_note = (
            f"Classement basé sur {metric_labels.get(metric, metric)}. "
            "Ces écarts sont associés aux alertes et ne prouvent pas une cause."
        )

        card = f"""
<div class="month-card">
  <div class="month-card-header">
    <div class="month-label">{mois}</div>
    {badges}
    <div style="margin-left:auto;display:flex;gap:8px;align-items:center;font-size:12px;color:var(--muted)">
      {kpi_list} &nbsp; {status_badge}
      {"<span style='color:var(--warn);font-size:11px'>gabarit utilisé</span>" if gabarit else ""}
    </div>
  </div>
  <div class="month-card-body">
    <div class="month-text">{txt_display}</div>
    <p class="analysis-note">{dimension_note}</p>
    <div style="display:flex;gap:16px;font-size:13px;color:var(--muted);margin-bottom:16px;flex-wrap:wrap">
      {f'<span>{promo_info}</span>' if promo_info else ""}
      {f'<span>{marge_neg_info}</span>' if marge_neg_info else ""}
    </div>
    <div class="two-col">
      <div>{cats}</div>
      <div>{regs}</div>
      <div>{products}</div>
    </div>
  </div>
</div>"""
        cards.append(card)
    return "\n".join(cards)


def _build_kpi_rows(kpi_df):
    rows = []
    # Only show rows within the main analysis period or nearby
    for _, r in kpi_df.iterrows():
        ev = r.get("EvolutionCA")
        import math
        ev_str = f"{_format_fr(ev*100, 2, signed=True)} %" if ev is not None and not (isinstance(ev, float) and math.isnan(ev)) else "—"
        ev_cls = "neg" if (ev is not None and not (isinstance(ev, float) and math.isnan(ev)) and ev < 0) else "pos"
        mp = r.get("MargePct", 0)
        mp_cls = "neg" if mp < 0 else ""
        rows.append(
            f'<tr>'
            f'<td><strong>{r["AnneeMois"]}</strong></td>'
            f'<td class="num">{_format_fr(r["CA"], 0)}</td>'
            f'<td class="num {"neg" if r["Marge"]<0 else ""}">{_format_fr(r["Marge"], 0)}</td>'
            f'<td class="num {mp_cls}">{_format_fr(r["MargePct"]*100, 2)} %</td>'
            f'<td class="num">{_format_fr(int(r["Quantite"]), 0)}</td>'
            f'<td class="num">{_format_fr(int(r["NbCommandes"]), 0)}</td>'
            f'<td class="num">{_format_fr(r["PanierMoyen"], 0)}</td>'
            f'<td class="num">{_format_fr(r["PartPromo"]*100, 2)} %</td>'
            f'<td class="num {ev_cls}">{ev_str}</td>'
            f'</tr>'
        )
    return "".join(rows)


def _build_html(state):
    import pandas as pd

    kpi_df   = state.get("kpi")
    alertes  = state.get("alertes", [])
    faits    = state.get("faits", [])
    groupes  = state.get("faits_groupes") or _regrouper(faits)
    textes   = state.get("textes", [])
    synthese = state.get("synthese") or ""
    val      = state.get("validation", [])

    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    from config import PERIODE_ANALYSE, FENETRE_ZSCORE, SEUIL_ZSCORE, MAX_ALERTES
    periode = (f"{kpi_df['AnneeMois'].min()} → {kpi_df['AnneeMois'].max()}"
               if kpi_df is not None and not kpi_df.empty else "—")
    periode_detection = f"{PERIODE_ANALYSE[0]} → {PERIODE_ANALYSE[1]}"
    nb_alertes = len(alertes)
    gabarit_count = sum(1 for item in val if item.get("remplace_par_gabarit"))
    guide = (
        "<ul>"
        "<li><strong>CA</strong> = somme des ventes ; <strong>marge</strong> = CA − coût ; "
        "<strong>taux de marge</strong> = marge / CA ; <strong>panier moyen global</strong> = CA total / "
        "commandes distinctes totales. La part promo utilise PromotionKey différent de 1.</li>"
        "<li><strong>Valeurs en %</strong> : MargePct et PartPromo sont affichés en pourcentage. "
        "L'écart relatif compare la valeur du mois à la moyenne de référence ; il peut dépasser 100 %.</li>"
        f"<li><strong>Alertes</strong> : chaque mois est comparé aux {FENETRE_ZSCORE} mois précédents. "
        f"Z-score absolu ≥ {2 * SEUIL_ZSCORE:g} = sévérité haute ; entre {SEUIL_ZSCORE:g} et "
        f"{2 * SEUIL_ZSCORE:g} = moyenne. Le rapport retient au plus les {MAX_ALERTES} alertes "
        "au Z-score le plus élevé dans la période de détection.</li>"
        "<li><strong>Dimensions</strong> : catégories, régions et produits sont classés selon la "
        "métrique indiquée sur chaque tableau. Ce sont des associations à examiner, pas des causes prouvées.</li>"
        "<li><strong>Validation</strong> : le contrôle vérifie que les nombres des commentaires figurent "
        "dans les faits calculés ; il ne certifie pas à lui seul les règles métier ni la source.</li>"
        + (f"<li><strong>Commentaires</strong> : {gabarit_count} commentaire(s) utilisent un gabarit de secours.</li>"
           if gabarit_count else "")
        + "</ul>"
    )

    return _HTML_TEMPLATE.format(
        css          = _CSS,
        date         = date_str,
        periode      = periode,
        periode_detection = periode_detection,
        nb_kpi_mois  = len(kpi_df) if kpi_df is not None else 0,
        nb_alertes   = nb_alertes,
        nb_mois_alertes = len(groupes),
        synthese     = escape(synthese).replace("\n", "<br>"),
        guide        = guide,
        kpi_cards    = _build_kpi_cards(kpi_df) if kpi_df is not None else "",
        alertes_rows = _build_alertes_rows(alertes),
        month_cards  = _build_month_cards(groupes, textes, val),
        kpi_rows     = _build_kpi_rows(kpi_df) if kpi_df is not None else "",
    )


def _build_csv(state):
    """CSV : une ligne par alerte avec le texte d'analyse associé."""
    alertes = state.get("alertes", [])
    faits   = state.get("faits", [])
    groupes = state.get("faits_groupes") or _regrouper(faits)
    textes  = state.get("textes", [])
    val     = state.get("validation", [])

    # map mois -> texte / validation
    texte_map = {}
    val_map   = {}
    for g, t in zip(groupes, textes or []):
        texte_map[g["alerte"]["AnneeMois"]] = t or ""
    for v in (val or []):
        val_map[v["mois"]] = "; ".join(v.get("problemes", [])) or "OK"

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "AnneeMois", "KPI", "Valeur", "Moyenne_ref",
        "ZScore", "Ecart_pct", "Ecart_annee_prec",
        "Severite", "Validation", "Texte_analyse",
    ])
    for a in alertes:
        mois = a["AnneeMois"]
        writer.writerow([
            mois,
            a.get("KPI", ""),
            a.get("Valeur", ""),
            a.get("Moyenne_ref", ""),
            a.get("ZScore", ""),
            a.get("Ecart_pct", ""),
            a.get("Ecart_annee_prec", ""),
            a.get("Severite", ""),
            val_map.get(mois, ""),
            texte_map.get(mois, ""),
        ])
    return buf.getvalue()


def _build_pdf(state, destination):
    """Crée une version PDF paginée et lisible de toutes les sections du rapport."""
    import numpy as np
    from xml.sax.saxutils import escape
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, LongTable,
    )

    kpi_df = state.get("kpi")
    alertes = state.get("alertes", [])
    faits = state.get("faits", [])
    groupes = state.get("faits_groupes") or _regrouper(faits)
    textes = state.get("textes", [])
    validation = {item["mois"]: item for item in state.get("validation", [])}
    synthese = state.get("synthese") or "Synthèse IA indisponible. Les chiffres détaillés restent disponibles dans ce rapport."

    def clean(value):
        text = str(value if value is not None else "—")
        text = (text.replace("\u202f", " ").replace("\u00a0", " ")
                    .replace("\u2011", "-").replace("\u2013", "-")
                    .replace("\u2014", "-").replace("\u2212", "-"))
        return escape(text).replace("\n", "<br/>")

    def number(value, decimals=2, suffix=""):
        try:
            val = float(value)
            if not np.isfinite(val):
                return "—"
            formatted = f"{val:,.{decimals}f}".replace(",", " ").replace(".", ",")
            return f"{formatted}{suffix}"
        except (TypeError, ValueError):
            return "—"

    def pct(value, decimals=2):
        try:
            val = float(value)
            return number(val * 100, decimals, " %") if np.isfinite(val) else "—"
        except (TypeError, ValueError):
            return "—"

    page_size = landscape(A4)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=page_size,
        leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title="Rapport complet PerfPulse BI", author="PerfPulse BI",
    )
    base = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=base["Title"], fontName="Helvetica-Bold",
        fontSize=21, leading=25, textColor=colors.HexColor("#312e81"),
        alignment=TA_LEFT, spaceAfter=5 * mm,
    )
    h1 = ParagraphStyle(
        "SectionHeading", parent=base["Heading1"], fontName="Helvetica-Bold",
        fontSize=15, leading=18, textColor=colors.HexColor("#312e81"),
        spaceBefore=3 * mm, spaceAfter=3 * mm,
    )
    h2 = ParagraphStyle(
        "SubHeading", parent=base["Heading2"], fontName="Helvetica-Bold",
        fontSize=11, leading=14, textColor=colors.HexColor("#0f766e"),
        spaceBefore=2 * mm, spaceAfter=2 * mm,
    )
    body = ParagraphStyle(
        "ReportBody", parent=base["BodyText"], fontName="Helvetica",
        fontSize=9, leading=13, spaceAfter=3 * mm,
    )
    small = ParagraphStyle(
        "TableCell", parent=body, fontSize=7.5, leading=9,
        spaceAfter=0, wordWrap="CJK",
    )
    header_cell = ParagraphStyle(
        "TableHeader", parent=small, fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    def para(value, style=small):
        return Paragraph(clean(value), style)

    def make_table(rows, widths, repeat=1, font_size=7.5):
        converted = [
            [para(value, header_cell if row_idx == 0 else small) for value in row]
            for row_idx, row in enumerate(rows)
        ]
        table = LongTable(converted, colWidths=widths, repeatRows=repeat, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#312e81")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return table

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    from config import PERIODE_ANALYSE, FENETRE_ZSCORE, SEUIL_ZSCORE
    story = [
        Paragraph("Rapport complet d'analyse des performances", title_style),
        para(f"Généré le {now} | Période analysée : {PERIODE_ANALYSE[0]} à {PERIODE_ANALYSE[1]} | "
             f"{len(alertes)} alertes sur {len(groupes)} mois", body),
        Paragraph("Synthèse générale", h1),
        para(synthese, body),
        Paragraph("Indicateurs clés", h1),
    ]

    if kpi_df is not None:
        ca_total = float(kpi_df["CA"].sum())
        marge_total = float(kpi_df["Marge"].sum())
        kpi_rows = [
            ["Indicateur", "Résultat", "Détail"],
            ["Chiffre d'affaires", number(ca_total, 2) + " EUR", f"{len(kpi_df)} mois"],
            ["Marge totale", number(marge_total, 2) + " EUR", f"Taux global : {pct(marge_total / ca_total if ca_total else 0)}"],
            ["Quantité vendue", number(kpi_df["Quantite"].sum(), 0), "Unités"],
            ["Commandes distinctes", number(kpi_df["NbCommandes"].sum(), 0), "Sur toute la période"],
            ["Part promotionnelle moyenne", pct(kpi_df["PartPromo"].mean()), "Moyenne des mois"],
            ["Panier moyen mensuel", number(kpi_df["PanierMoyen"].mean(), 2) + " EUR", "Moyenne des mois"],
        ]
        story.append(make_table(kpi_rows, [55 * mm, 55 * mm, 150 * mm]))
    story += [
        Spacer(1, 4 * mm),
        para(f"Méthode de détection : comparaison de chaque mois aux {FENETRE_ZSCORE} mois précédents, "
             f"seuil |Z-score| ≥ {SEUIL_ZSCORE}. Les dimensions décrivent des écarts associés, pas des causes prouvées.", body),
        PageBreak(),
        Paragraph("Tableau complet des alertes", h1),
    ]

    alert_rows = [["Mois", "KPI", "Valeur", "Moyenne de réf.", "Z-score", "Écart relatif", "Sévérité"]]
    for a in alertes:
        ratio = a.get("KPI") in {"MargePct", "PartPromo"}
        val_fmt = pct(a.get("Valeur")) if ratio else number(a.get("Valeur"), 2)
        avg_fmt = pct(a.get("Moyenne_ref")) if ratio else number(a.get("Moyenne_ref"), 2)
        ecart = a.get("Ecart_pct")
        alert_rows.append([
            a.get("AnneeMois", ""), a.get("KPI", ""), val_fmt, avg_fmt,
            number(a.get("ZScore"), 2), pct(ecart), a.get("Severite", ""),
        ])
    story.append(make_table(alert_rows, [25 * mm, 31 * mm, 35 * mm, 39 * mm, 25 * mm, 36 * mm, 25 * mm]))

    story += [PageBreak(), Paragraph("Analyses détaillées par mois", h1)]
    textes_map = {g["alerte"]["AnneeMois"]: t for g, t in zip(groupes, textes)}
    for index, group in enumerate(groupes):
        month = group["alerte"]["AnneeMois"]
        month_alerts = group.get("alertes_du_mois", [group["alerte"]])
        story.append(Paragraph(f"{month} — {len(month_alerts)} alerte(s)", h2))
        detail_rows = [["KPI", "Valeur", "Moyenne de référence", "Z-score", "Écart relatif", "Sévérité"]]
        for a in month_alerts:
            ratio = a.get("KPI") in {"MargePct", "PartPromo"}
            detail_rows.append([
                a.get("KPI", ""),
                pct(a.get("Valeur")) if ratio else number(a.get("Valeur"), 2),
                pct(a.get("Moyenne_ref")) if ratio else number(a.get("Moyenne_ref"), 2),
                number(a.get("ZScore"), 2), pct(a.get("Ecart_pct")), a.get("Severite", ""),
            ])
        story.append(make_table(detail_rows, [35 * mm, 35 * mm, 45 * mm, 25 * mm, 35 * mm, 25 * mm]))
        if textes_map.get(month):
            story.append(Spacer(1, 2 * mm))
            story.append(para(textes_map[month], body))

        promo = group.get("promotions", {})
        negative = group.get("lignes_a_marge_negative", {})
        info = []
        if promo.get("part_promo_mois") is not None:
            info.append(f"Part du CA en promotion : {pct(promo['part_promo_mois'])}")
        if negative:
            info.append(f"Lignes à marge négative : {number(negative.get('nombre'), 0)}; "
                        f"perte totale : {number(negative.get('perte_totale'), 2)} EUR")
        if info:
            story.append(para(" | ".join(info), body))

        dimension_rows = [["Dimension", "Valeur du mois", "Référence moyenne", "Écart"]]
        for label, key in [("Catégorie", "top_categories"), ("Région", "top_regions"), ("Produit", "top_produits")]:
            for item in group.get(key, []):
                dimension_rows.append([
                    f"{label} : {item.get('nom', '')}",
                    number(item.get("valeur_mois"), 2),
                    number(item.get("valeur_reference"), 2),
                    number(item.get("ecart"), 2),
                ])
        if len(dimension_rows) > 1:
            story.append(make_table(dimension_rows, [78 * mm, 48 * mm, 48 * mm, 40 * mm]))
        result = validation.get(month, {})
        status = "Vérification des chiffres : OK" if not result.get("problemes") else "Texte à revoir : " + "; ".join(result["problemes"])
        if result.get("remplace_par_gabarit"):
            status += " (commentaire de secours utilisé)"
        story.append(para(status, small))
        story.append(Spacer(1, 5 * mm))

    if kpi_df is not None:
        story += [PageBreak(), Paragraph("Historique mensuel complet des KPI", h1)]
        monthly_rows = [["Mois", "CA (EUR)", "Marge (EUR)", "Marge %", "Quantité", "Commandes", "Panier moyen (EUR)", "Part promo", "Évolution CA"]]
        for _, row in kpi_df.iterrows():
            monthly_rows.append([
                str(row["AnneeMois"]), number(row["CA"], 2), number(row["Marge"], 2),
                pct(row["MargePct"]), number(row["Quantite"], 0), number(row["NbCommandes"], 0),
                number(row["PanierMoyen"], 2), pct(row["PartPromo"]), pct(row["EvolutionCA"]),
            ])
        story.append(make_table(monthly_rows, [25 * mm, 35 * mm, 35 * mm, 25 * mm, 24 * mm, 24 * mm, 40 * mm, 25 * mm, 30 * mm]))

    def add_page_number(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(14 * mm, 8 * mm, "PerfPulse BI — Rapport complet")
        canvas.drawRightString(page_size[0] - 14 * mm, 8 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    destination.write_bytes(buffer.getvalue())


# ──────────────────────────────────────────────────────────
# Agent public entry point
# ──────────────────────────────────────────────────────────

def report(state):
    """Génère les rapports HTML, PDF et CSV dans output/."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Persiste aussi les données utilisées par l'API du tableau de bord.
    # Sans ces fichiers, seuls les rapports téléchargeables sont disponibles.
    def json_default(value):
        if hasattr(value, "item"):
            return value.item()
        raise TypeError(f"Type non sérialisable en JSON : {type(value).__name__}")

    (OUTPUT_DIR / "faits.json").write_text(
        json.dumps(state.get("faits", []), ensure_ascii=False, default=json_default, allow_nan=False),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "textes.json").write_text(
        json.dumps({"textes": state.get("textes", []), "synthese": state.get("synthese", "")},
                   ensure_ascii=False, default=json_default, allow_nan=False),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "validation.json").write_text(
        json.dumps(state.get("validation", []), ensure_ascii=False, default=json_default, allow_nan=False),
        encoding="utf-8",
    )

    html_content = _build_html(state)
    csv_content  = _build_csv(state)
    pdf_path = OUTPUT_DIR / "rapport_complet.pdf"
    _build_pdf(state, pdf_path)

    html_path = OUTPUT_DIR / "rapport.html"
    csv_path  = OUTPUT_DIR / "rapport_alertes.csv"

    html_path.write_text(html_content, encoding="utf-8")
    csv_path.write_text(csv_content,  encoding="utf-8")

    print(f"Rapport généré : {html_path}")
    print(f"PDF généré     : {pdf_path}")
    print(f"CSV généré     : {csv_path}")

    return {
        "report": {
            "html": str(html_path),
            "pdf": str(pdf_path),
            "csv":  str(csv_path),
        }
    }
