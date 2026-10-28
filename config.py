from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return False


load_dotenv(Path(__file__).resolve().parent / ".env")

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
AGENTS_DIR = ROOT / "agents"
PBIX_PATH = DATA_DIR / "finalbi.pbix"

# --- Groq ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MODEL_NAME = GROQ_MODEL           # alias, pour ne rien casser
PAUSE_GROQ = 2                    # secondes entre deux appels (quota gratuit)
MAX_ALERTES = 15                  # limite le quota Groq

# --- Données ---
PROMO_SANS = 1                    # PromotionKey = "pas de promotion"

# --- Détection d'anomalies (étape 4) ---
FENETRE_ZSCORE = 6                # mois
SEUIL_ZSCORE = 2.0
PLANCHER_STD = 0.10               # écart-type minimal = 10 % de la moyenne
PERIODE_ANALYSE = ("2017-07", "2020-05")   # seule période continue

# Anciens seuils, non utilisés par les agents actuels
THRESHOLD_ALERT = 0.10
THRESHOLD_VARIATION = 0.15
MAX_ESSAIS = 2            # 1 génération + 1 relance
TOLERANCE_NOMBRE = 0.011  # tolérance relative pour les arrondis

if __name__ == "__main__":
    print(f"ROOT={ROOT}")
    print(f"DATA_DIR={DATA_DIR}")
    print(f"OUTPUT_DIR={OUTPUT_DIR}")
