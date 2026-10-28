from __future__ import annotations

import re
from config import MAX_ESSAIS, TOLERANCE_NOMBRE

NOMBRE = re.compile(r"-?\d[\d\s\u202f\u00a0]*(?:[.,]\d+)?")
MOIS = re.compile(r"\b\d{4}-\d{2}\b")

MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"]
SANS_ACCENT = {"février": "fevrier", "août": "aout", "décembre": "decembre"}


def _collecter(obj, acc):
    """Récupère tous les nombres des faits (et les versions en %)."""
    if isinstance(obj, dict):
        for v in obj.values():
            _collecter(v, acc)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _collecter(v, acc)
    elif isinstance(obj, bool) or obj is None:
        return
    elif isinstance(obj, (int, float)):
        if obj == obj:  # ignore NaN
            acc.add(abs(float(obj)))
            acc.add(abs(float(obj)) * 100)  # 0.3469 -> 34.69 %
    elif isinstance(obj, str):
        for m in NOMBRE.findall(obj):
            n = _vers_float(m)
            if n is not None:
                acc.add(abs(n))


def _vers_float(s):
    s = s.replace("\u202f", "").replace("\u00a0", "").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _noms(obj, cle):
    """Noms (catégories, régions) listés dans les faits."""
    return [x["nom"] for x in obj.get(cle, []) if x.get("nom")]


def _proche(n, autorises):
    for a in autorises:
        if a == 0:
            if n == 0:
                return True
        elif abs(n - a) / a <= TOLERANCE_NOMBRE or abs(n - a) <= 0.01:
            return True
    return False


def _normaliser(texte):
    """Normalise les tirets unicode (en-dash, tiret insécable, etc.) en tiret ASCII."""
    return (texte
            .replace("\u2011", "-")   # tiret insécable (non-breaking hyphen)
            .replace("\u2013", "-")   # tiret demi-cadratin (en-dash)
            .replace("\u2014", "-"))  # tiret cadratin (em-dash)


def _mois_cite(texte, mois):
    """Accepte 2018-06, 06/2018 ou « juin 2018 ».

    Normalise aussi les tirets unicode que les LLM insèrent parfois
    (ex. '2019\u201107' au lieu de '2019-07').
    """
    norm = _normaliser(texte)
    annee, num = mois.split("-")
    if mois in norm or f"{num}/{annee}" in norm:
        return True
    nom = MOIS_FR[int(num) - 1]
    bas = texte.lower()
    return annee in texte and (nom in bas or SANS_ACCENT.get(nom, nom) in bas)


def verifier(texte, groupe):
    """Retourne la liste des problèmes (liste vide = texte valide)."""
    if not texte:
        return ["texte vide"]
    problemes = []
    mois = groupe["alerte"]["AnneeMois"]

    autorises = set()
    _collecter(groupe, autorises)

    # Les mois (2018-06) et leurs composantes (2018, 6) sont autorisés
    # Normalise les tirets unicode avant d'appliquer la regex MOIS
    texte_norm = _normaliser(texte)
    texte_sans_mois = MOIS.sub(" ", texte_norm)
    for m in MOIS.findall(texte_norm):
        if m != mois and m not in groupe.get("periode_reference", ""):
            problemes.append(f"mois inattendu : {m}")
    annee, num = mois.split("-")
    autorises.update({float(annee), float(num)})
    for m in re.findall(r"\d{4}-\d{2}", groupe.get("periode_reference", "")):
        a, n = m.split("-")
        autorises.update({float(a), float(n)})

    # Tous les nombres du texte doivent exister dans les faits
    for m in NOMBRE.findall(texte_sans_mois):
        n = _vers_float(m)
        if n is not None and not _proche(abs(n), autorises):
            problemes.append(f"nombre absent des faits : {m.strip()}")

    # Mois, catégorie et région doivent être cités
    bas = texte.lower()
    if not _mois_cite(texte, mois):
        problemes.append("mois non cité")
    cats = _noms(groupe, "top_categories")
    if cats and not any(c.lower() in bas for c in cats):
        problemes.append("catégorie non citée")
    regs = _noms(groupe, "top_regions")
    if regs and not any(r.lower() in bas for r in regs):
        problemes.append("région non citée")
    return problemes


def gabarit(groupe):
    """Texte généré sans LLM, uniquement à partir des faits."""
    mois = groupe["alerte"]["AnneeMois"]
    parties = []
    for a in groupe["alertes_du_mois"]:
        e = a.get("Ecart_pct")
        ecart = f"{e * 100:+.2f} %" if isinstance(e, (int, float)) and e == e else "écart non calculé"
        parties.append(f"{a['KPI']} ({ecart} par rapport à la période de référence)")
    cats, regs = _noms(groupe, "top_categories"), _noms(groupe, "top_regions")
    txt = f"En {mois}, alertes sur : " + ", ".join(parties) + "."
    if cats:
        txt += f" Catégorie la plus concernée : {cats[0]}."
    if regs:
        txt += f" Région la plus concernée : {regs[0]}."
    pr = groupe.get("promotions", {}).get("part_promo_mois")
    if pr is not None:
        txt += f" Part du CA en promotion : {pr * 100:.2f} %."
    return txt


def validate(state):
    groupes = state["faits_groupes"]
    textes = list(state["textes"])
    essais = state.get("essais", 1)
    groq_unavailable = state.get("groq_unavailable", False)
    groq_fallback_used = state.get("groq_fallback_used", False)

    if len(textes) != len(groupes):
        raise ValueError(
            f"Nombre de textes différent du nombre de groupes : {len(textes)} != {len(groupes)}"
        )

    rapport = []
    tous_ok = True
    for g, t in zip(groupes, textes):
        pb = verifier(t, g)
        rapport.append({"mois": g["alerte"]["AnneeMois"], "problemes": pb})
        if pb:
            tous_ok = False
            print(f"Rejet {g['alerte']['AnneeMois']} : {pb}")

    # Après la dernière relance : on remplace les textes invalides par le gabarit
    if not tous_ok and (essais >= MAX_ESSAIS or groq_unavailable):
        for i, (g, t) in enumerate(zip(groupes, textes)):
            problemes = verifier(t, g)
            if problemes:
                textes[i] = gabarit(g)
                rapport[i]["problemes"] = verifier(textes[i], g)
                rapport[i]["remplace_par_gabarit"] = True
        tous_ok = all(not item["problemes"] for item in rapport)

    synthese = state.get("synthese")
    if groq_unavailable and not synthese:
        if groq_fallback_used:
            synthese = (
                "La génération IA est indisponible car le quota Groq est atteint. "
                "Les commentaires détaillés utilisent des gabarits basés sur les données calculées."
            )
        else:
            synthese = (
                "La synthèse IA n'a pas pu être générée car le quota Groq est atteint. "
                "Les commentaires vérifiés restent disponibles ci-dessous."
            )

    return {"textes": textes, "ok": tous_ok, "validation": rapport,
            "synthese": synthese}
