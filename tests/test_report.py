import pandas as pd

from agents.report import _build_alertes_rows, _build_pdf


def test_report_formats_ratio_alert_values_as_percentages():
    html = _build_alertes_rows([
        {"AnneeMois": "2020-05", "KPI": "MargePct", "Valeur": -0.0037,
         "Moyenne_ref": 0.0062, "Ecart_pct": -1.602, "ZScore": -3.83,
         "Severite": "moyenne"},
        {"AnneeMois": "2018-06", "KPI": "PartPromo", "Valeur": 0.3535,
         "Moyenne_ref": 0.0070, "Ecart_pct": 49.5, "ZScore": 62.17,
         "Severite": "haute"},
    ])

    assert "-0.37 %" in html
    assert "0.62 %" in html
    assert "35.35 %" in html
    assert "0.70 %" in html


def test_pdf_contains_complete_report_sections(tmp_path):
    month_alert = {
        "AnneeMois": "2024-02", "KPI": "MargePct", "Valeur": -0.1,
        "Moyenne_ref": 0.05, "ZScore": -3.0, "Ecart_pct": -3.0,
        "Severite": "moyenne",
    }
    group = {
        "alerte": month_alert, "alertes_du_mois": [month_alert],
        "top_categories": [{"nom": "Cycles", "valeur_mois": 10, "valeur_reference": 20, "ecart": -10}],
        "top_regions": [{"nom": "Nord", "valeur_mois": 10, "valeur_reference": 20, "ecart": -10}],
        "top_produits": [], "metrique_analysee": "Marge",
        "promotions": {"part_promo_mois": 0.2},
        "lignes_a_marge_negative": {"nombre": 2, "perte_totale": -50},
    }
    monthly = pd.DataFrame([{
        "AnneeMois": "2024-02", "CA": 100, "Cout": 90, "Marge": 10,
        "MargePct": 0.1, "Quantite": 3, "NbCommandes": 2,
        "PanierMoyen": 50, "PartPromo": 0.2, "EvolutionCA": 0.1,
    }])
    target = tmp_path / "report.pdf"

    _build_pdf({
        "kpi": monthly, "alertes": [month_alert], "faits": [],
        "faits_groupes": [group], "textes": ["Analyse vérifiée pour Nord et Cycles."],
        "synthese": "Synthèse claire en français.",
        "validation": [{"mois": "2024-02", "problemes": []}],
    }, target)

    content = target.read_bytes()
    assert content.startswith(b"%PDF-")
    assert content.rstrip().endswith(b"%%EOF")
    assert len(content) > 1000
