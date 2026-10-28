from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import AsyncGenerator

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import DATA_DIR, OUTPUT_DIR, PBIX_PATH
from graph import app as graph_app

app = FastAPI(title="PerfPulse BI Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).resolve().parent / "web"
WEB_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

CURRENT_PBIX = PBIX_PATH


# ──────────────────────────────────────────────────────────
# Data helpers
# ──────────────────────────────────────────────────────────

def _clean_nans(obj):
    """Recursively replaces NaN and inf with None for valid JSON serialization."""
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _clean_nans(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_nans(x) for x in obj]
    return obj


def load_dashboard_data():
    """Charge et prépare toutes les métriques pour les graphiques et le dashboard."""
    kpi_file = OUTPUT_DIR / "kpi_mensuels.csv"
    faits_file = OUTPUT_DIR / "faits.json"
    textes_file = OUTPUT_DIR / "textes.json"
    validation_file = OUTPUT_DIR / "validation.json"

    if not (kpi_file.exists() and faits_file.exists()):
        return {"ready": False}

    kpi_df = pd.read_csv(kpi_file)
    kpi_df = kpi_df.sort_values("AnneeMois")

    with open(faits_file, "r", encoding="utf-8") as f:
        faits = json.load(f)

    textes_data = {}
    if textes_file.exists():
        with open(textes_file, "r", encoding="utf-8") as f:
            textes_data = json.load(f)

    val_data = []
    if validation_file.exists():
        with open(validation_file, "r", encoding="utf-8") as f:
            val_data = json.load(f)

    val_map = {v["mois"]: v for v in val_data}

    # Alertes par mois pour les courbes
    alertes_par_mois = {}
    alertes_list = []
    for f in faits:
        alt = f.get("alerte", {})
        mois = alt.get("AnneeMois")
        if mois:
            alertes_par_mois.setdefault(mois, []).append(alt)
            alertes_list.append(alt)

    # Préparation des séries pour Chart.js
    kpi_series = []
    for _, row in kpi_df.iterrows():
        mois = str(row["AnneeMois"])
        alts = alertes_par_mois.get(mois, [])
        is_alert = len(alts) > 0
        sev_max = "haute" if any(a.get("Severite") == "haute" for a in alts) else ("moyenne" if is_alert else "normale")

        ca = float(row.get("CA", 0) or 0)
        marge = float(row.get("Marge", 0) or 0)
        marge_pct = float(row.get("MargePct", 0) or 0) * 100 if pd.notna(row.get("MargePct")) else None
        evo = float(row.get("EvolutionCA", 0) or 0) * 100 if pd.notna(row.get("EvolutionCA")) else None
        panier = float(row.get("PanierMoyen", 0) or 0) if pd.notna(row.get("PanierMoyen")) else None
        qte = int(row.get("Quantite", 0) or 0) if pd.notna(row.get("Quantite")) else None

        kpi_series.append({
            "mois": mois,
            "ca": round(ca, 2),
            "marge": round(marge, 2),
            "marge_pct": round(marge_pct, 2) if marge_pct is not None else None,
            "evolution": round(evo, 2) if evo is not None else None,
            "panier": round(panier, 2) if panier is not None else None,
            "quantite": qte,
            "part_promo": round(float(row.get("PartPromo", 0) or 0) * 100, 2)
                           if pd.notna(row.get("PartPromo")) else None,
            "is_alert": is_alert,
            "alert_count": len(alts),
            "severite": sev_max,
            "alertes": alts,
        })

    # Regroupement des analyses par mois
    analyses = []
    mois_groupes = {}
    for f in faits:
        mois = f["alerte"]["AnneeMois"]
        mois_groupes.setdefault(mois, []).append(f)

    # Récupération des textes rédigés
    textes_list = textes_data.get("textes", [])
    textes_map = {}
    # Les textes correspondent aux mois_groupes dans l'ordre
    for mois, t in zip(mois_groupes.keys(), textes_list):
        textes_map[mois] = t

    for mois, items in mois_groupes.items():
        premier = items[0]
        alts = [x["alerte"] for x in items]
        val = val_map.get(mois, {"problemes": [], "remplace_par_gabarit": False})
        analyses.append({
            "mois": mois,
            "alertes": alts,
            "texte": textes_map.get(mois, ""),
            "causes": {
                "produits": premier.get("top_produits", []),
                "territoires": premier.get("top_regions", []),
                "revendeurs": [],
                "metrique": premier.get("metrique_analysee"),
            },
            "validation": val,
        })

    # Stats résumées
    total_ca = float(kpi_df["CA"].sum()) if "CA" in kpi_df else 0.0
    total_marge = float(kpi_df["Marge"].sum()) if "Marge" in kpi_df else 0.0
    avg_marge_pct = (total_marge / total_ca * 100) if total_ca > 0 else 0.0
    nb_alertes = len(alertes_list)
    nb_haute = sum(1 for a in alertes_list if a.get("Severite") == "haute")
    nb_moyenne = nb_alertes - nb_haute

    payload = {
        "ready": True,
        "stats": {
            "total_ca": round(total_ca, 2),
            "total_marge": round(total_marge, 2),
            "avg_marge_pct": round(avg_marge_pct, 2),
            "nb_mois": len(kpi_df),
            "nb_alertes": nb_alertes,
            "nb_haute": nb_haute,
            "nb_moyenne": nb_moyenne,
            "validation_ok": all(len(v.get("problemes", [])) == 0 for v in val_data) if val_data else True,
        },
        "kpi_series": kpi_series,
        "alertes": alertes_list,
        "analyses": analyses,
        "synthese": textes_data.get("synthese", ""),
        "validation": val_data,
    }
    return _clean_nans(payload)


def clear_pipeline_results():
    """Supprime les résultats publiés pour empêcher leur réutilisation."""
    if not OUTPUT_DIR.exists():
        return 0
    deleted = 0
    for path in OUTPUT_DIR.iterdir():
        if path.is_file():
            path.unlink()
            deleted += 1
    return deleted


# ──────────────────────────────────────────────────────────
# API Endpoints
# ──────────────────────────────────────────────────────────

@app.get("/")
def get_index():
    index_file = WEB_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>Dashboard en cours de construction...</h1>")
    return FileResponse(index_file)


@app.get("/api/status")
def get_status():
    global CURRENT_PBIX
    pbix_ok = CURRENT_PBIX.exists()
    pbix_size = CURRENT_PBIX.stat().st_size if pbix_ok else 0
    kpi_file = OUTPUT_DIR / "kpi_mensuels.csv"

    return {
        "pbix": {
            "path": str(CURRENT_PBIX),
            "name": CURRENT_PBIX.name,
            "exists": pbix_ok,
            "size_mb": round(pbix_size / (1024 * 1024), 2) if pbix_ok else 0,
        },
        "has_results": kpi_file.exists(),
        "agents": [
            {"id": "extract", "nom": "Extract", "desc": "Extraction des 9 tables depuis le PBIX"},
            {"id": "kpi", "nom": "Calcul KPI", "desc": "Calcul du CA, Marge, Évolution temporelle"},
            {"id": "detect", "nom": "Détection", "desc": "Détection statistique d'anomalies (Z-Score)"},
            {"id": "analyse", "nom": "Analyse Causale", "desc": "Décomposition par catégorie & territoire"},
            {"id": "write", "nom": "Rédaction IA", "desc": "Génération des commentaires avec Groq LLM"},
            {"id": "validate", "nom": "Validation", "desc": "Contrôle anti-hallucination & des dates"},
            {"id": "report", "nom": "Rapports", "desc": "Production des livrables HTML & CSV"},
        ]
    }


@app.post("/api/upload-pbix")
async def upload_pbix(file: UploadFile = File(...)):
    global CURRENT_PBIX
    if not file.filename.endswith(".pbix"):
        return {"error": "Seuls les fichiers avec extension .pbix sont acceptés."}

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    destination = DATA_DIR / file.filename
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    CURRENT_PBIX = destination

    # Test rapide de lecture avec pbixray
    try:
        from pbixray import PBIXRay
        ray = PBIXRay(str(destination))
        tables = [t for t in ray.tables if not t.startswith("_")]
    except Exception as e:
        return {
            "success": False,
            "error": f"Erreur de lecture du modèle PBIX : {str(e)}"
        }

    return {
        "success": True,
        "name": file.filename,
        "size_mb": round(destination.stat().st_size / (1024 * 1024), 2),
        "tables": tables,
        "tables_count": len(tables),
    }


@app.get("/api/run-stream")
async def run_pipeline_stream(pbix_path: str = Query(None)):
    """Exécute les agents LangGraph pas à pas et transmet la progression en direct via SSE."""
    global CURRENT_PBIX
    target_pbix = Path(pbix_path) if pbix_path else CURRENT_PBIX

    async def event_generator() -> AsyncGenerator[str, None]:
        # Écarte les résultats précédents avant toute nouvelle exécution.
        clear_pipeline_results()
        yield f"data: {json.dumps({'event': 'start', 'message': f'Démarrage du pipeline sur {target_pbix.name}...' }, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.3)

        agent_steps = [
            ("extract", "Extraction des tables depuis le PBIX...", 1),
            ("kpi", "Calcul des KPIs mensuels et de la marge...", 2),
            ("detect", "Détection des anomalies par Z-score...", 3),
            ("analyse", "Diagnostic des causes racines (produits, territoires)...", 4),
            ("write", "Rédaction des synthèses analytiques avec Groq...", 5),
            ("validate", "Vérification anti-hallucination des chiffres...", 6),
            ("report", "Génération des rapports HTML et CSV...", 7),
        ]

        loop = asyncio.get_running_loop()
        events = asyncio.Queue()
        finished = object()

        def run_sync_stream():
            try:
                for step_dict in graph_app.stream({"essais": 0, "pbix_path": str(target_pbix)}):
                    loop.call_soon_threadsafe(events.put_nowait, step_dict)
            except Exception as e:
                loop.call_soon_threadsafe(events.put_nowait, {"error": str(e)})
            finally:
                loop.call_soon_threadsafe(events.put_nowait, finished)

        # Exécute le stream dans un thread séparé
        # Keep the event loop free while the blocking graph runs in its worker.

        # Pour une meilleure animation temps réel, on émet des étapes
        yield f"data: {json.dumps({'event': 'agent_start', 'agent': 'extract', 'step': 1, 'message': 'Extraction du modèle Power BI...'}, ensure_ascii=False)}\n\n"

        worker = loop.run_in_executor(None, run_sync_stream)

        # Parcours des résultats reçus
        while True:
            chunk = await events.get()
            if chunk is finished:
                break
            if "error" in chunk:
                yield f"data: {json.dumps({'event': 'error', 'message': chunk['error']}, ensure_ascii=False)}\n\n"
                await worker
                return

            for node_name, node_val in chunk.items():
                summary = ""
                if node_name == "extract":
                    nb = len(node_val.get("tables", {}))
                    summary = f"{nb} tables extraites avec succès"
                elif node_name == "kpi":
                    df = node_val.get("kpi")
                    summary = f"{len(df)} mois de ventes calculés" if df is not None else "KPIs calculés"
                elif node_name == "detect":
                    alts = node_val.get("alertes", [])
                    summary = f"{len(alts)} alertes détectées"
                elif node_name == "analyse":
                    faits = node_val.get("faits", [])
                    mois = {f.get("alerte", {}).get("AnneeMois") for f in faits}
                    summary = f"Causes racines analysées pour {len(mois)} mois"
                elif node_name == "write":
                    txts = node_val.get("textes", [])
                    if node_val.get("groq_fallback_used"):
                        summary = "Quota Groq atteint : commentaires de secours générés"
                    elif node_val.get("groq_unavailable"):
                        summary = "Quota Groq atteint pendant la synthèse; commentaires vérifiés conservés"
                    else:
                        summary = f"{len(txts)} analyses rédigées par Groq LLM"
                elif node_name == "validate":
                    ok = node_val.get("ok", True)
                    summary = "Validation 100% réussie (aucun chiffre inventé)" if ok else "Corrections appliquées"
                elif node_name == "report":
                    summary = "Rapports HTML, PDF et CSV générés dans output/"

                yield f"data: {json.dumps({'event': 'agent_complete', 'agent': node_name, 'message': summary}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.2)

        await worker

        # Envoi de la fin avec chargement des données
        dashboard_data = load_dashboard_data()
        yield f"data: {json.dumps({'event': 'complete', 'data': dashboard_data}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/data")
def get_data():
    return load_dashboard_data()


@app.get("/api/download/report.html")
def download_html():
    p = OUTPUT_DIR / "rapport.html"
    if p.exists():
        return FileResponse(p, filename="rapport_analyste.html", media_type="text/html")
    return {"error": "Fichier introuvable. Exécutez d'abord le pipeline."}


@app.get("/api/download/report.pdf")
def download_pdf():
    p = OUTPUT_DIR / "rapport_complet.pdf"
    if p.exists():
        return FileResponse(p, filename="rapport_complet.pdf", media_type="application/pdf")
    return {"error": "Fichier introuvable. Exécutez d'abord le pipeline."}


@app.get("/api/download/rapport_alertes.csv")
def download_csv():
    p = OUTPUT_DIR / "rapport_alertes.csv"
    if p.exists():
        return FileResponse(p, filename="rapport_alertes.csv", media_type="text/csv")
    return {"error": "Fichier introuvable. Exécutez d'abord le pipeline."}


@app.post("/api/reset")
@app.get("/api/reset")
def reset_execution():
    """Supprime les fichiers générés dans output/ pour repartir à zéro."""
    count = clear_pipeline_results()
    return {"success": True, "deleted_files": count}


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="PerfPulse Dashboard Server")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8501")), help="Port d'écoute (défaut: 8501)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Hôte (défaut: 127.0.0.1)")
    args = parser.parse_args()

    print(f"Démarrage du Dashboard sur http://{args.host}:{args.port}")
    uvicorn.run("server:app", host=args.host, port=args.port, reload=True)
