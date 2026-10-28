from __future__ import annotations

import pytest

import agents.validate as validate_agent


@pytest.fixture
def facts_group():
    alert = {
        "AnneeMois": "2024-02", "KPI": "CA", "Valeur": 200.0,
        "Moyenne_ref": 100.0, "ZScore": 2.0, "Ecart_pct": 0.5,
        "Severite": "haute",
    }
    return {
        "alerte": alert,
        "alertes_du_mois": [alert],
        "periode_reference": "2023-08 à 2024-01",
        "top_categories": [{"nom": "Widget", "valeur_mois": 200.0,
                            "valeur_reference": 100.0, "ecart": 100.0}],
        "top_regions": [{"nom": "East", "valeur_mois": 200.0,
                         "valeur_reference": 100.0, "ecart": 100.0}],
        "promotions": {"part_promo_mois": None},
    }


def test_accepts_text_grounded_in_facts(facts_group):
    text = "En 2024-02, le CA vaut 200, avec un écart de 50 %. Widget et East sont les dimensions principales."

    assert validate_agent.verifier(text, facts_group) == []


@pytest.mark.parametrize("text", [
    "En 2024-02, CA vaut 999 pour Widget à East.",
    "En 2024-03, CA vaut 200 pour Widget à East.",
    "En 2024-02, CA vaut 200 pour Widget à West.",
])
def test_rejects_unsupported_number_month_or_missing_region(text, facts_group):
    assert validate_agent.verifier(text, facts_group)


def test_validate_rejects_missing_text_instead_of_silently_truncating(facts_group):
    with pytest.raises(ValueError, match="Nombre de textes"):
        validate_agent.validate({"faits_groupes": [facts_group], "textes": [], "essais": 1})


def test_template_fallback_updates_validation_status(facts_group, monkeypatch):
    monkeypatch.setattr(validate_agent, "MAX_ESSAIS", 2)
    result = validate_agent.validate({
        "faits_groupes": [facts_group],
        "textes": ["En 2024-02, une hausse de 999 à Widget dans East."],
        "essais": 2,
    })

    assert result["ok"] is True
    assert result["validation"][0]["remplace_par_gabarit"] is True
    assert result["validation"][0]["problemes"] == []


def test_invalid_template_cannot_be_reported_as_valid(facts_group, monkeypatch):
    monkeypatch.setattr(validate_agent, "MAX_ESSAIS", 2)
    monkeypatch.setattr(validate_agent, "gabarit", lambda _group: "")
    result = validate_agent.validate({
        "faits_groupes": [facts_group], "textes": ["texte erroné"], "essais": 2,
    })

    assert result["ok"] is False
    assert result["validation"][0]["problemes"] == ["texte vide"]


def test_rate_limit_uses_template_without_waiting_for_retry(facts_group):
    result = validate_agent.validate({
        "faits_groupes": [facts_group], "textes": [None], "essais": 1,
        "groq_unavailable": True,
    })

    assert result["ok"] is True
    assert result["validation"][0]["remplace_par_gabarit"] is True
    assert result["validation"][0]["problemes"] == []
    assert "quota Groq" in result["synthese"]
