# PerfPulse-Agent-IA-d-analyse-des-performances-d-entreprise
Un mini-agent IA qui surveille des KPI, détecte les évolutions notables, identifie le produit ou la région concernés et rédige une courte conclusion. Power BI sert d'interface de restitution et de validation.
<img width="1257" height="623" alt="Capture d’écran 2026-10-28 193642" src="https://github.com/user-attachments/assets/64568ae9-a555-4315-8b1b-ffe88b6791ed" />
## 📌 Présentation

**PerfPulse** est une solution de Business Intelligence augmentée par l'intelligence artificielle, conçue pour analyser les performances commerciales d'une entreprise.

Le projet combine la visualisation des données avec **Microsoft Power BI** et un agent intelligent développé en **Python**, utilisant un modèle de langage via **Groq API**.

L'objectif est de transformer des données commerciales en analyses compréhensibles, de détecter automatiquement les anomalies et de proposer des pistes d'amélioration pour faciliter la prise de décision.

### 🎯 Objectifs

- Centraliser et analyser les données commerciales.
- Visualiser les indicateurs clés de performance (KPI).
- Détecter automatiquement les variations inhabituelles.
- Identifier les catégories et les régions concernées.
- Analyser les effets prix, volume et mix.
- Étudier l'impact des promotions sur la rentabilité.
- Générer des analyses métier avec l'IA.
- Vérifier la cohérence des textes générés.
- Produire des rapports exploitables par les décideurs.

---

## 🏗️ Architecture générale

```text
             ┌───────────────────────┐
             │   Données commerciales│
             └───────────┬───────────┘
                         │
                         ▼
             ┌───────────────────────┐
             │       Power BI        │
             │ Modèle et indicateurs │
             └───────────┬───────────┘
                         │
                         ▼
             ┌───────────────────────┐
             │   Extraction Python   │
             │     des 9 tables      │
             └───────────┬───────────┘
                         │
                         ▼
             ┌───────────────────────┐
             │  Détection d'anomalies│
             │     sur les KPI       │
             └───────────┬───────────┘
                         │
                         ▼
             ┌───────────────────────┐
             │  Analyse métier       │
             │ Prix / Volume / Mix   │
             │ Promotions / Marges   │
             └───────────┬───────────┘
                         │
                         ▼
             ┌───────────────────────┐
             │      Groq API         │
             │  Génération des textes│
             └───────────┬───────────┘
                         │
                         ▼
             ┌───────────────────────┐
             │ Validation automatique│
             │ Chiffres / Cohérence  │
             └───────────┬───────────┘
                         │
                ┌────────┴─────────┐
                │                  │
                ▼                  ▼
          Texte validé       Texte rejeté
                │                  │
                │           Nouvelle tentative
                │                  │
                │           Gabarit de secours
                │           si échec persistant
                └────────┬─────────┘
                         ▼
             ┌───────────────────────┐
             │    Rapports finaux    │
             │      JSON / HTML      │
             └───────────────────────┘
```

---

## 🛠️ Technologies utilisées

| Technologie | Utilisation |
|---|---|
| Python | Développement de l'agent d'analyse |
| Microsoft Power BI | Modélisation et visualisation des données |
| Groq API | Génération d'analyses en langage naturel |
| GPT-OSS-120B | Modèle IA utilisé pour les analyses |
| JSON | Stockage des analyses et résultats |
| HTML | Génération de rapports consultables |
| PowerShell | Exécution sous Windows |
| Git / GitHub | Gestion des versions |

---

## 📊 Dashboard Power BI

Le dashboard permet de suivre les principaux indicateurs commerciaux de l'entreprise.

### Indicateurs clés

- **Chiffre d'affaires (CA)** : montant total des ventes.
- **Marge** : différence entre les revenus et les coûts retenus.
- **Marge %** : rentabilité rapportée au chiffre d'affaires.
- **Nombre de commandes** : volume d'activité commerciale.
- **CA par catégorie** : contribution des différentes familles de produits.
- **CA par région** : répartition géographique des ventes.
- **CA par mois** : évolution temporelle de l'activité.
- **Évolution mensuelle du CA** : comparaison avec le mois précédent.

### Visualisations

Le tableau de bord comprend :

1. Un filtre interactif par année.
2. Des cartes KPI pour les résultats globaux.
3. Un histogramme du CA par catégorie.
4. Une courbe d'évolution mensuelle du CA.
5. Un graphique du CA par région commerciale.
6. Un tableau comparatif des performances mensuelles.

### Exemple de résultats

Pour la sélection 2018–2019 présentée dans le dashboard :

| KPI | Valeur affichée |
|---|---|
| Chiffre d'affaires | 56,83 M€ |
| Marge | 637 K€ |
| Taux de marge | 1,12 % |
| Nombre de commandes | 2 536 |

Ces valeurs correspondent à un exemple de contexte de filtrage Power BI et peuvent changer selon la sélection.

---

## 🧠 Agent IA PerfPulse

L'agent intelligent complète les visualisations Power BI par une analyse automatique des performances.

### 1. Extraction des données

L'agent exploite les tables du modèle commercial :

```text
ColorFormats
DimDate
DimEmployee
DimEmployeeSalesTerritory
DimProduct
DimReseller
DimSalesTerritory
FactSales
ResellerSalesTargets
```

### 2. Détection des anomalies

Le moteur analyse les indicateurs pour repérer les variations inhabituelles.

Exemples :

- Baisse importante de la marge.
- Augmentation inhabituelle du chiffre d'affaires.
- Variation importante des quantités vendues.
- Progression anormale de la part promotionnelle.
- Dégradation de la rentabilité malgré une hausse des ventes.

Les analyses peuvent exploiter des écarts relatifs, des périodes de référence et des Z-scores.

### 3. Analyse des facteurs de variation

PerfPulse analyse la variation du chiffre d'affaires à travers trois effets :

**Effet volume**

Contribution des variations de quantités vendues.

**Effet prix**

Contribution des changements de prix de vente.

**Effet mix**

Contribution des changements dans la composition des ventes.

La décomposition utilisée dans les résultats vérifie la relation :

```text
Variation totale du CA
    = Effet volume
    + Effet mix
    + Effet prix
```

### 4. Analyse de la rentabilité

L'agent examine également :

- Les transactions à marge négative.
- La marge des ventes promotionnelles.
- La marge des ventes hors promotion.
- La part du chiffre d'affaires réalisée en promotion.
- Les catégories présentant des écarts importants.
- Les régions commerciales les plus concernées.

### 5. Génération d'analyses avec Groq

L'agent utilise un modèle de langage pour transformer les résultats chiffrés en analyses métier.

Les textes générés présentent notamment :

- Les anomalies détectées.
- Les indicateurs concernés.
- Les périodes de référence.
- Les écarts observés.
- Les facteurs associés aux variations.
- Les impacts financiers.
- Les pistes d'action à examiner.

---

## 🛡️ Validation des analyses IA

Afin de limiter les erreurs des modèles génératifs, PerfPulse intègre une étape de validation automatique.

### Contrôles effectués

Le validateur vérifie notamment :

- La présence des informations obligatoires.
- La cohérence des valeurs numériques.
- Les pourcentages et les points de pourcentage.
- Les références mensuelles et agrégées.
- La cohérence des périodes analysées.
- La présence des indicateurs attendus.

### Gestion des textes rejetés

Lorsqu'un texte ne respecte pas les règles de validation :

1. Les problèmes sont identifiés.
2. Une nouvelle tentative peut être effectuée.
3. Le texte généré est vérifié à nouveau.
4. En cas d'échec persistant, un gabarit déterministe est utilisé.

L'historique des tentatives est conservé pour faciliter l'audit des résultats.

---

## ⚠️ Gestion des erreurs Groq

PerfPulse prend en compte les limitations de l'API Groq.

Lorsqu'une erreur de quota HTTP 429 est détectée :

- L'erreur est enregistrée.
- Les appels IA suivants peuvent être bloqués pour l'exécution.
- Les rapports restants sont générés à partir de gabarits de secours.
- Les événements API sont conservés dans les résultats de validation.

Cette approche permet de continuer à produire les rapports même lorsque le service IA est temporairement indisponible.

---

## 📄 Rapports générés

Les résultats sont enregistrés dans le dossier :

```text
output/
```

Ils comprennent notamment :

**Analyses JSON**

Contiennent les textes produits, les périodes analysées et les informations de validation.

**Historique de validation**

Permet de retrouver les tentatives, les rejets, les problèmes détectés et les événements API.

**Rapport HTML**

Présente les analyses mensuelles avec leur statut :

- Accepté par l'IA.
- Remplacé par un gabarit de secours.

**Indicateurs de qualité**

Permettent de mesurer :

- Le taux d'acceptation au premier essai.
- Le taux d'acceptation finale par l'IA.
- Le taux de recours aux gabarits.
- Le nombre de tentatives IA.
- Les motifs de rejet.

---

## 📁 Organisation générale

```text
PerfPulse-Agent-IA-d-analyse-des-performances-d-entreprise/
│
├── main.py
│
├── output/
│   ├── ...
│   └── ...
│
├── .venv/
│
├── .env
│
├── .gitignore
│
└── README.md
```

> Cette structure présente les éléments principaux. Les modules Python supplémentaires et les fichiers Power BI peuvent être ajoutés selon l'organisation réelle du dépôt.

---

## 🚀 Installation et exécution

### Prérequis

- Windows avec PowerShell
- Python 3
- Accès au modèle de données Power BI
- Une clé API Groq
- Les dépendances Python du projet

### 1. Cloner le dépôt

```bash
git clone <URL_DU_DEPOT>
cd PerfPulse-Agent-IA-d-analyse-des-performances-d-entreprise
```

Remplacer `<URL_DU_DEPOT>` par l'adresse réelle du dépôt GitHub.

### 2. Créer l'environnement virtuel

Dans PowerShell :

```powershell
python -m venv .venv
```

Activer l'environnement :

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Installer les dépendances

Si le projet contient un fichier `requirements.txt` :

```powershell
pip install -r requirements.txt
```

### 4. Configurer Groq

Créer un fichier `.env` si la configuration du projet l'utilise :

```env
GROQ_API_KEY=votre_cle_api_groq
```

Ne jamais publier une clé API dans GitHub.

### 5. Exécuter le projet

```powershell
python main.py
```

### Exemple de sortie

```text
9 tables extraites
15 alertes détectées
Terminé : 15 alertes, 6 textes.
Voir le dossier output/
```

Le nombre d'alertes et de textes peut varier selon les données et les paramètres.

---

## 🔒 Sécurité

Les éléments suivants ne doivent pas être publiés :

```gitignore
# Environnement Python
.venv/
__pycache__/
*.pyc

# Variables et secrets
.env
.env.*
!.env.example

# Fichiers temporaires
*.log

# Fichiers générés
output/
```

Les rapports générés peuvent contenir des données commerciales sensibles. Leur publication doit être autorisée avant tout partage.

---

## 📈 Exemple d'analyse métier

### Anomalie de rentabilité — Juillet 2019

**Constat**

Le taux de marge atteint -4,34 % contre une moyenne de référence de 4,21 %, soit une baisse de 8,55 points de pourcentage.

**Facteurs associés**

La catégorie Bikes et la région Southwest présentent des écarts négatifs importants. Les ventes promotionnelles affichent également une marge négative.

**Impact**

844 lignes présentent une marge négative, pour une perte cumulée de 227 165,35 €.

**Pistes à examiner**

- Analyser les produits Bikes les moins rentables.
- Vérifier les remises commerciales appliquées.
- Examiner les transactions à marge négative.
- Comparer la rentabilité des régions.

Ces recommandations constituent des pistes d'investigation et non des relations causales démontrées.

---

## 🔮 Perspectives d'amélioration

Les évolutions possibles du projet comprennent :

- Création d'un tableau de bord dédié à la qualité de l'agent IA.
- Ajout d'un système de priorisation des anomalies.
- Automatisation des tests de cohérence métier.
- Réduction de la consommation de tokens.
- Mise en cache des analyses déjà validées.
- Génération de rapports PDF.
- Intégration des analyses IA dans Power BI.
- Ajout d'un historique comparatif des anomalies.
- Développement d'un système d'alertes automatiques.
- Amélioration des recommandations selon les catégories et régions.

---

## 🎯 Conclusion

**PerfPulse** associe la Business Intelligence et l'intelligence artificielle pour faciliter l'analyse des performances commerciales.

Le projet ne se limite pas à afficher les indicateurs : il détecte les anomalies, analyse les écarts, génère des explications et applique des contrôles de validation avant de produire les rapports finaux.

L'objectif est de fournir une solution d'aide à la décision plus intelligente, explicable et fiable.

---

## 📜 Licence

Licence à définir selon les conditions de diffusion du projet.
