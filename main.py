from dotenv import load_dotenv
load_dotenv()                      # charge GROQ_API_KEY depuis .env (doit rester en premier)

import json
from config import OUTPUT_DIR
from graph import app


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    resultat = app.invoke({"essais": 0})

    # Faits calculés par l'Analyste (étape 5)
    with open(OUTPUT_DIR / "faits.json", "w", encoding="utf-8") as f:
        json.dump(resultat["faits"], f, ensure_ascii=False, indent=1, default=str)

    # Textes rédigés par Groq puis validés (étapes 6 et 7)
    with open(OUTPUT_DIR / "textes.json", "w", encoding="utf-8") as f:
        json.dump({"textes": resultat["textes"], "synthese": resultat["synthese"]},
                  f, ensure_ascii=False, indent=1)

    # Rapport du Validateur (étape 7)
    with open(OUTPUT_DIR / "validation.json", "w", encoding="utf-8") as f:
        json.dump(resultat["validation"], f, ensure_ascii=False, indent=1)

    print(f"Terminé : {len(resultat['faits'])} alertes, "
          f"{len(resultat['textes'])} textes. Voir le dossier output/")
    rpt = resultat.get("report", {})
    if rpt.get("html"):
        print(f"  -> Rapport HTML : {rpt['html']}")
    if rpt.get("csv"):
        print(f"  -> CSV alertes  : {rpt['csv']}")
    return resultat


if __name__ == "__main__":
    main()
