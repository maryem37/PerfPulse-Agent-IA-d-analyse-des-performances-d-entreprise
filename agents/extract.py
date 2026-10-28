from pathlib import Path

from pbixray import PBIXRay

try:
    from config import PBIX_PATH
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from config import PBIX_PATH


def extract(state):
    if not PBIX_PATH.exists():
        raise FileNotFoundError(f"Fichier PBIX introuvable : {PBIX_PATH}")

    data_dir = Path(PBIX_PATH).parent
    data_dir.mkdir(parents=True, exist_ok=True)
    m = PBIXRay(str(PBIX_PATH))

    tables = {}
    for nom in m.tables:
        df = m.get_table(nom)
        if df.shape[0] == 0:          # ignore les tables vides (ex. _Mesures)
            continue
        tables[nom] = df
        df.to_csv(data_dir / f"{nom}.csv", index=False, encoding="utf-8")

    # Les mesures DAX sont aussi exportées (utile pour documenter les KPI)
    m.dax_measures.to_csv(data_dir / "mesures_dax.csv", index=False, encoding="utf-8")

    # Contrôle minimal : les tables indispensables doivent exister
    for requis in ["FactSales", "DimDate", "DimProduct", "DimSalesTerritory"]:
        if requis not in tables:
            raise ValueError(f"Table obligatoire absente : {requis}")

    print(f"{len(tables)} tables extraites :", ", ".join(tables))
    return {"tables": tables, "mesures_dax": m.dax_measures.to_dict("records")}


if __name__ == "__main__":
    extract({})