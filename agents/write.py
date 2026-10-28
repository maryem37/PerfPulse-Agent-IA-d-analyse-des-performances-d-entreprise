import json
import time
from collections import OrderedDict
from langchain_groq import ChatGroq
from config import GROQ_MODEL, PAUSE_GROQ

llm = ChatGroq(model=GROQ_MODEL, temperature=0)

PROMPT = """Tu es analyste BI. Rédige 3 phrases en français à partir des faits ci-dessous.
RÈGLES :
- INTERDIT d'inventer un chiffre, une cause commerciale ou une explication absente des faits.
- Recopie les nombres tels quels (pas d'arrondi, pas de calcul nouveau).
- Cite : le mois sous la forme exacte AAAA-MM (par exemple 2018-06), les KPI en alerte avec leur écart, la catégorie principale, la région principale.
- Si les faits montrent des promotions ou des lignes à marge négative, mentionne-les.
- Ne propose aucune cause (la cause réelle n'est pas dans les données).
Faits : {faits}"""

PROMPT_SYNTHESE = """Tu es analyste BI. Rédige une synthèse de 4 phrases maximum en français
à partir de ces résumés d'anomalies. N'invente aucun chiffre et aucune cause.
Résumés : {textes}"""


def regrouper_par_mois(faits):
    """Un seul texte par mois : on fusionne les alertes du même mois."""
    groupes = OrderedDict()
    for f in faits:
        mois = f["alerte"]["AnneeMois"]
        groupes.setdefault(mois, []).append(f)
    regroupes = []
    for mois, liste in groupes.items():
        base = dict(liste[0])  # décomposition, tops, promos : identiques dans le mois
        base["alertes_du_mois"] = [x["alerte"] for x in liste]
        regroupes.append(base)
    return regroupes


def _appel(prompt):
    for tentative in range(3):
        try:
            return llm.invoke(prompt).content.strip()
        except Exception as e:
            message = str(e).lower()
            if (getattr(e, "status_code", None) == 429
                    or "rate_limit_exceeded" in message
                    or "tokens per day" in message):
                print("Quota Groq atteint; passage aux commentaires de secours.")
                return None
            print(f"Erreur Groq ({e}), nouvelle tentative...")
            time.sleep(10 * (tentative + 1))
    return None  # le Validateur utilisera le gabarit


def write(state):
    essais = state.get("essais", 0) + 1
    groupes = state.get("faits_groupes") or regrouper_par_mois(state["faits"])
    groq_unavailable = state.get("groq_unavailable", False)

    textes = []
    for g in groupes:
        if groq_unavailable:
            textes.append(None)
            continue
        txt = _appel(PROMPT.format(faits=json.dumps(g, ensure_ascii=False, default=str)))
        textes.append(txt)
        if txt is None:
            groq_unavailable = True
        else:
            time.sleep(PAUSE_GROQ)

    synthese = None
    if not groq_unavailable:
        synthese = _appel(PROMPT_SYNTHESE.format(
            textes=json.dumps([t for t in textes if t], ensure_ascii=False)))
        groq_unavailable = synthese is None

    return {"faits_groupes": groupes, "textes": textes,
            "synthese": synthese, "essais": essais,
            "groq_unavailable": groq_unavailable,
            "groq_fallback_used": any(text is None for text in textes)}
