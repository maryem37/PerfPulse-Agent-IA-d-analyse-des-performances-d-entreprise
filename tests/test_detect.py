from __future__ import annotations

import pandas as pd
import pytest

import agents.detect as detect_agent


def _monthly_kpis(values):
    months = pd.period_range("2020-01", periods=len(values), freq="M").astype(str)
    return pd.DataFrame({
        "AnneeMois": months,
        "CA": values,
        "Marge": [20.0] * len(values),
        "MargePct": [0.2] * len(values),
        "Quantite": [10.0] * len(values),
        "PanierMoyen": [100.0] * len(values),
        "PartPromo": [0.1] * len(values),
    })


def test_detect_uses_previous_six_months_and_expected_z_score(tmp_path, monkeypatch):
    monkeypatch.setattr(detect_agent, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(detect_agent, "PERIODE_ANALYSE", ("2020-01", "2020-08"))
    monkeypatch.setattr(detect_agent, "FENETRE_ZSCORE", 6)
    monkeypatch.setattr(detect_agent, "SEUIL_ZSCORE", 2.0)
    monkeypatch.setattr(detect_agent, "PLANCHER_STD", 0.10)
    monkeypatch.setattr(detect_agent, "MAX_ALERTES", 15)

    result = detect_agent.detect({"kpi": _monthly_kpis([100] * 6 + [200, 100])})
    ca_alert = next(a for a in result["alertes"]
                    if a["AnneeMois"] == "2020-07" and a["KPI"] == "CA")

    # Les six références valent 100 (écart-type nul); le plancher vaut 10.
    assert ca_alert["Moyenne_ref"] == pytest.approx(100)
    assert ca_alert["ZScore"] == pytest.approx(10)
    assert ca_alert["Ecart_pct"] == pytest.approx(1)
    assert ca_alert["Severite"] == "haute"
    assert not any(a["AnneeMois"] == "2020-06" for a in result["alertes"])


def test_detect_respects_max_alert_count(tmp_path, monkeypatch):
    monkeypatch.setattr(detect_agent, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(detect_agent, "PERIODE_ANALYSE", ("2020-01", "2020-08"))
    monkeypatch.setattr(detect_agent, "FENETRE_ZSCORE", 6)
    monkeypatch.setattr(detect_agent, "SEUIL_ZSCORE", 2.0)
    monkeypatch.setattr(detect_agent, "PLANCHER_STD", 0.10)
    monkeypatch.setattr(detect_agent, "MAX_ALERTES", 1)

    result = detect_agent.detect({"kpi": _monthly_kpis([100] * 6 + [200, 300])})

    assert len(result["alertes"]) == 1
    assert result["alertes"][0]["AnneeMois"] == "2020-07"
    assert result["alertes"][0]["ZScore"] == pytest.approx(10)


def test_detect_skips_months_with_insufficient_reference_data(tmp_path, monkeypatch):
    monkeypatch.setattr(detect_agent, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(detect_agent, "PERIODE_ANALYSE", ("2020-01", "2020-08"))
    monkeypatch.setattr(detect_agent, "FENETRE_ZSCORE", 6)
    monkeypatch.setattr(detect_agent, "SEUIL_ZSCORE", 2.0)
    monkeypatch.setattr(detect_agent, "PLANCHER_STD", 0.10)
    monkeypatch.setattr(detect_agent, "MAX_ALERTES", 15)
    kpis = _monthly_kpis([100] * 8)
    kpis.loc[:4, "CA"] = float("nan")

    result = detect_agent.detect({"kpi": kpis})

    assert result["alertes"] == []
