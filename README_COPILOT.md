# README_COPILOT.md - CONTEXTE TECHNIQUE & RÈGLES DE DÉVELOPPEMENT

⚠️ **IMPORTANT POUR L'IA** : 
Ce fichier contient la vérité source du projet **N.D.A.I**. Toutes les générations de code doivent STRICTEMENT respecter les contraintes ci-dessous.

---

## 1. STACK TECHNIQUE (IMMUABLE)
* **Langage :** Python
* **Base de données :** PostgreSQL (Image officielle). Utilisation mixte : Relationnel (Sales) + JSONB (Reviews).
* **Orchestration :** Apache Airflow (Docker officiel).
* **Ingestion API :** FastAPI.
* **Stockage Fichiers (Batch) :** LocalStack (Simulation S3).
* **NLP / IA :** NLTK (Librairie `VADER` pour l'analyse de sentiment).
* **Visualization :** Streamlit.
* **Infrastructure :** Docker Compose (100% conteneurisé).

---

## 2. ARCHITECTURE DES PIPELINES

### PIPELINE A : Ventes (Sales) - Approche ETL (Batch)
1.  **Source :** Fichiers CSV (ex: `sales_data.csv`).
2.  **Stockage Initial :** Upload dans un Bucket S3 (simulé par **LocalStack**).
3.  **Traitement (Airflow) :**
    * Extract depuis S3.
    * Transform (Cleaning, Cast Date) via Pandas en RAM.
    * **Load :** Insertion dans la table PostgreSQL `sales` (Schéma Relationnel).

### PIPELINE B : Reviews (Feedback) - Approche ELT (Hybride & Temps Réel)
1.  **Sources Mixtes :**
    * **Historique :** Un fichier `feedback_data.json` existe déjà (simulation de données passées).
    * **Nouveaux Avis :** De nouveaux feedbacks arrivent en temps réel via des appels HTTP POST.
2.  **Ingestion (FastAPI) :**
    * L'API expose un endpoint pour recevoir les nouveaux avis.
    * L'API (ou un script d'init) doit permettre de charger le fichier JSON historique initial.
3.  **Load (Immédiat) :** Insertion brute dans PostgreSQL table `reviews` (Colonne `raw_data` type **JSONB**). **PAS de passage par S3/LocalStack ici.**
4.  **Traitement (Airflow - Asynchrone) :**
    * DAG récupère les lignes où le score est NULL.
    * Processing IA : NLTK VADER analyse le texte (champ `comment` dans le JSON).
    * Update : Mise à jour de la colonne `sentiment_score` dans PostgreSQL.

---

## 3. MODÉLISATION DE DONNÉES (POSTGRESQL)

Les tables doivent respecter cette structure :

#### Table `sales` (Relationnel)
* `id` : Serial PK
* `sale_date` : DATE (Format source YYYY-MM-DD)
* `username` : VARCHAR (Non utilisé pour la jointure)
* `country` : VARCHAR
* `product` : VARCHAR
* `quantity` : INTEGER
* `unit_price` : FLOAT
* `total_amount` : FLOAT

#### Table `reviews` (Semi-structuré)
* `id` : Serial PK
* `raw_data` : JSONB (Contient tout l'objet JSON reçu)
* `sentiment_score` : FLOAT (Calculé par l'IA a posteriori, nullable)
* `ingestion_date` : TIMESTAMP (Default NOW)

#### Vue SQL `view_global_kpi` (La Fusion)
Nous ne créons **PAS** de table physique de fusion.
Créer une vue qui :
1.  Agrège les `sales` par `sale_date` et `country` (Sum amount, Sum quantity).
2.  Agrège les `reviews` (extraites du JSONB) par `feedback_date` (Moyenne sentiment_score).
3.  Fait un **LEFT JOIN** sur la date (`sale_date` = `feedback_date`).

---

## 4. ORCHESTRATION (AIRFLOW DAGS)

Un seul DAG `sales_pipeline` contient les deux pipelines avec des tâches indépendantes :

### Tâches du DAG `sales_pipeline` :

1.  **`ingest_to_s3`** (Pipeline A)
    * Trigger : Quotidien (ex: `@daily`).
    * Logic : Extract sales_data.csv from `data/raw/` -> Upload to LocalStack S3.
    * Module : `src/ingest_s3.py`

2.  **`clean_data`** (Pipeline A)
    * Trigger : Après `ingest_to_s3`.
    * Logic : Download from S3 -> Pandas cleaning/transformation.
    * Module : `src/clean_data.py`
    * Output : Cleaned CSV saved to `data/processed/`.

3.  **`load_to_postgres`** (Pipeline A)
    * Trigger : Après `clean_data`.
    * Logic : Insert cleaned data into PostgreSQL `sales` table.
    * Module : `src/load_postgres.py`

4.  **`reviews_ai_processing`** (Pipeline B)
    * Trigger : Fréquent (ex: `*/30 * * * *`) - Indépendant du Pipeline A.
    * Logic : Select rows from `reviews` where `sentiment_score` IS NULL -> NLTK VADER Analyze -> Update SQL.
    * Modules : Utilise les modules `src/*.py` pour l'interaction DB.

### Structure des Modules Python :
* `src/ingest_s3.py` : Gère les uploads vers LocalStack S3.
* `src/clean_data.py` : Nettoyage et transformation des données (Pandas).
* `src/load_postgres.py` : Insertion et mise à jour dans PostgreSQL.

---

## 5. RÈGLES DE CODAGE & DOCKER

* **Docker Compose :** Doit inclure les services `postgres`, `airflow-webserver`, `airflow-scheduler`, `fastapi`, `streamlit`, `localstack`.
* **Networking :** Tous les services doivent être sur le même réseau docker `ndai_network`.
* **Variables d'Env :** Utiliser un fichier `.env` pour les crédentials DB et endpoints.
* **Gestion d'erreur :** Les scripts doivent logger les erreurs mais ne pas faire crasher le conteneur (Try/Except blocks).

---

## 📊 Data Samples

**Sales Data (CSV):**
```csv
username,sale_date,country,product,quantity,unit_price,total_amount
user149,2025-05-10,India,Chicken Nuggets,5,11.14,55.7
user914,2025-06-05,USA,Fried Wings,2,14.53,29.06
user739,2025-07-15,France,Grilled Tenders,1,8.76,8.76
```

**Reviews Data (JSON):**
```json
[
    {
        "username": "user_fb68",
        "feedback_date": "2025-04-04",
        "campaign_id": "CAMP147",
        "comment": "Great campaign!"
    },
    {
        "username": "user_fb46",
        "feedback_date": "2025-02-23",
        "campaign_id": "CAMP892",
        "comment": "Not very engaging."
    },
    {
        "username": "user_fb81",
        "feedback_date": "2025-09-21",
        "campaign_id": "CAMP274",
        "comment": "Loved the product presentation."
    }
]


## 📂 Project Structure

```bash
.
├── dags/
│   └── sales_pipeline.py       # Main Airflow DAG (Pipelines A & B réunis)
├── data/
│   ├── raw/
│   │   ├── sales_data.csv      # Sales data source
│   │   └── feedback_data.json  # Reviews/Feedback history
│   └── processed/
│       └── cleaned_sales_data.csv # Output du nettoyage
├── src/                        # Python ETL modules
│   ├── __init__.py
│   ├── clean_data.py           # Cleaning & transformation (Pandas)
│   ├── ingest_s3.py            # S3 ingestion (LocalStack)
│   └── load_postgres.py        # PostgreSQL insert/update
├── explore_data.ipynb          # Data exploration notebook
├── docker-compose.yml          # Docker infrastructure
├── README.md                   # User documentation
├── README_COPILOT.md           # Technical specifications (this file)
├── requirements.txt            # Python dependencies
├── logs/                       # Airflow DAG execution logs
└── localstack_data/            # LocalStack S3 simulation storage
```

## ✅ Ce qui est déjà fait

1. **Infrastructure :** Le `docker-compose.yml` tourne avec succès (Airflow, Postgres, LocalStack).
2. **Pipeline A (Batch) :** TERMINÉE. Le DAG `sales_pipeline.py` fonctionne avec `PythonOperator`. Les données brutes vont dans S3, sont processées par Pandas, et sont chargées proprement (TRUNCATE + INSERT) dans PostgreSQL via les scripts du dossier `src/`.
3. **Git :** Projet versionné avec un `.gitignore` propre.

## 🎯 Prochain Objectif : Pipeline B (Temps Réel - Micro-Batch FastAPI)

### Objectif
Développer la **Pipeline B** pour l'ingestion et le traitement temps réel des avis clients via une architecture micro-batch légère.

### Contraintes Immuables
- **AUCUN Kafka** — Pas de broker de messages complexe.
- **AUCUN Spark Streaming** — Pas de traitement distribué.
- **AUCUN Airflow** — Cette partie reste indépendante de l'orchestration Airflow.

### Architecture Détaillée

#### 1. API FastAPI (`src/api_feedback.py`)
- Expose un endpoint `POST /feedbacks` qui reçoit une liste d'objets JSON.
- Utilise **Pydantic** pour valider chaque objet individuellement (granularité par objet, pas par batch).
- Chaque objet valide :
  - Est inséré dans la table PostgreSQL `feedbacks`.
  - Reçoit une analyse de sentiment via **NLTK** → colonne `sentiments` (1 = Positif/Neutre, 0 = Négatif).
- Chaque objet invalide :
  - Est inséré dans la table PostgreSQL `rejected_feedbacks` avec le motif du rejet.
  - N'est pas traité.

#### 2. Micro-Batch Script (`__main__.py PUSH N`)
- Script local qui envoie N avis depuis `data/raw/feedback_data.json` vers l'API FastAPI.
- Commande : `python __main__.py PUSH 5` envoie 5 avis.
- Réceptionne le rapport partiel (succès + rejets + métriques).

#### 3. Modèle de Données (PostgreSQL)

**Table `feedbacks`**
```sql
CREATE TABLE feedbacks (
  id SERIAL PRIMARY KEY,
  username VARCHAR,
  feedback_date DATE,
  campaign_id VARCHAR,
  comment TEXT,
  sentiments INT (0 ou 1),
  ingestion_date TIMESTAMP DEFAULT NOW()
);
```

**Table `rejected_feedbacks`**
```sql
CREATE TABLE rejected_feedbacks (
  id SERIAL PRIMARY KEY,
  raw_data TEXT,  -- JSON brut reçu
  rejection_reason VARCHAR,  -- Motif du rejet (ex: "missing 'comment'", "invalid date")
  ingestion_date TIMESTAMP DEFAULT NOW()
);
```

#### 4. Flux de Traitement
```
Client/Script
    ↓
POST /feedbacks [JSON array]
    ↓
FastAPI Endpoint
    ↓
Pydantic Validation (par objet)
    ↓
┌─── Valide ──────────────────────┐
│  NLTK Sentiment Analysis    │
│  Insert into feedbacks (+ score)│
└────────────────────────────────┘
│
└─── Invalide ────────────────────┐
│  Insert into rejected_feedbacks │
│  (avec motif du rejet)          │
└────────────────────────────────┘
    ↓
Response JSON:
{
  "success_count": 4,
  "rejection_count": 1,
  "quality_percentage": 80.0,
  "rejections": [
    {"index": 2, "reason": "missing 'campaign_id'"}
  ]
}
```

#### 5. Intégration Docker
- FastAPI doit être un **nouveau service** dans `docker-compose.yml`.
- Port : `8000` (Uvicorn).
- Dépendance : PostgreSQL doit être up avant le démarrage.
- Réseau : `ndai_network` (comme tous les autres services).

**Note :** Les dossiers `sql/`, `api/`, et `dashboard/` ne sont pas présents pour l'instant. Ils seront créés si nécessaire pour SQL scripts, FastAPI app, ou Streamlit dashboard.