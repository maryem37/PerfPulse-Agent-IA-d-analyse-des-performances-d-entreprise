from __future__ import annotations

from pathlib import Path

import pandas as pd

from agents.extract import extract
from agents.kpi import kpi
from config import DATA_DIR, OUTPUT_DIR


def ensure_kpi_csv() -> Path:
    output_file = OUTPUT_DIR / "kpi_mensuels.csv"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_file.exists():
        return output_file

    pbix_file = DATA_DIR / "finalbi.pbix"
    if not pbix_file.exists():
        raise FileNotFoundError(f"Fichier PBIX introuvable : {pbix_file}")

    state = extract({})
    kpi_state = kpi(state)
    if "kpi" not in kpi_state:
        raise RuntimeError("Le calcul KPI n’a pas produit de DataFrame.")

    if not output_file.exists():
        raise FileNotFoundError(f"Le fichier KPI n’a pas été généré : {output_file}")

    return output_file


def main():
    kpi_file = ensure_kpi_csv()
    k = pd.read_csv(kpi_file)
    print(f"KPI rows: {k.shape[0]}")
    print(k[k["AnneeMois"] == "2019-10"].T)
    return k


if __name__ == "__main__":
    main()