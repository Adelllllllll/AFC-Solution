import os
import json
import logging
# L'import "random" n'est plus nécessaire !
from typing import List, Dict, Any
from fastapi import FastAPI
import pandas as pd
from pydantic import BaseModel, ValidationError
from sqlalchemy import create_engine, text

# NOUVEAU : On importe la fonction depuis le fichier NLTK_Analysis
from src.sentiments_anaylisis import analyze_text_sentiment

# --- Configuration Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# --- Configuration Base de Données ---
DB_USER = os.getenv("POSTGRES_USER", "airflow")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_DB = os.getenv("POSTGRES_DB", "airflow")

# --- Initialisation FastAPI ---
app = FastAPI(
    title="N.D.A.I Feedback API", 
    description="API temps réel avec tolérance aux pannes (DLQ) et analyse NLP XLM-RoBERTa intégrée."
)

# --- Modèle Pydantic (Tolérance aux pannes) ---
class FeedbackInput(BaseModel):
    username: str
    feedback_date: str
    campaign_id: str
    comment: str

def get_db_engine():
    url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DB}"
    return create_engine(url)

def init_db():
    """Crée les DEUX tables : succès et rejets (DLQ)."""
    engine = get_db_engine()
    
    create_feedbacks_sql = """
    CREATE TABLE IF NOT EXISTS feedbacks (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50),
        feedback_date DATE,
        campaign_id VARCHAR(50),
        comment TEXT,
        sentiments INTEGER,  -- 1 pour Positif, 0 pour Négatif
        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_rejected_sql = """
    CREATE TABLE IF NOT EXISTS rejected_feedbacks (
        id SERIAL PRIMARY KEY,
        raw_payload JSONB,
        error_reason TEXT,
        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(create_feedbacks_sql))
            conn.execute(text(create_rejected_sql))
            conn.commit()
        logger.info("Tables 'feedbacks' et 'rejected_feedbacks' initialisées avec succès.")
    except Exception as e:
        logger.error(f"Erreur d'initialisation de la BDD : {e}")

@app.on_event("startup")
def on_startup():
    init_db()

# MODIFIÉ : On remplace le comportement aléatoire par l'IA NLTK
def set_sentiments(text_to_analyze: str) -> int:
    """
    Appelle le modèle NLP XLM-RoBERTa pour définir le sentiment.
    """
    return analyze_text_sentiment(text_to_analyze)

def update_local_json_export():
    """Exporte la table feedbacks en JSON physique dans data/processed/ de manière silencieuse."""
    try:
        engine = get_db_engine()
        df_export = pd.read_sql("SELECT * FROM feedbacks", engine)
        export_path = "/app/data/processed/feedbacks_export.json"
        df_export.to_json(export_path, orient="records", date_format="iso", force_ascii=False, indent=4)
        logger.info(f"✅ Export auto réussi : {len(df_export)} lignes sauvegardées dans le JSON.")
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'export automatique : {e}")

@app.get("/health")
def health_check():
    """Endpoint de santé pour Docker."""
    return {"status": "healthy"}

@app.post("/afc/api")
async def receive_feedbacks(payload: List[Dict[str, Any]]):
    """Endpoint cible pour le PUSH. Fait le tri entre bons et mauvais JSON."""
    logger.info(f"Réception d'un lot de {len(payload)} avis...")
    
    valid_feedbacks = []
    rejected_feedbacks = []
    
    # 1. TRI ET VALIDATION (DLQ)
    for item in payload:
        try:
            valid_item = FeedbackInput(**item)
            valid_feedbacks.append(valid_item)
        except ValidationError as e:
            rejected_feedbacks.append({
                "raw_payload": json.dumps(item),
                "error_reason": str(e)
            })
            
    # 2. ENRICHISSEMENT (IA) ET INSERTION
    engine = get_db_engine()
    
    with engine.connect() as conn:
        # A. Insertion des succès
        if valid_feedbacks:
            for fb in valid_feedbacks:
                # Appel de notre fonction IA
                sentiment_val = set_sentiments(fb.comment)
                
                insert_valid_sql = text("""
                    INSERT INTO feedbacks (username, feedback_date, campaign_id, comment, sentiments)
                    VALUES (:username, :feedback_date, :campaign_id, :comment, :sentiments)
                """)
                conn.execute(insert_valid_sql, {
                    "username": fb.username,
                    "feedback_date": fb.feedback_date,
                    "campaign_id": fb.campaign_id,
                    "comment": fb.comment,
                    "sentiments": sentiment_val
                })
        
        # B. Insertion des rejets
        if rejected_feedbacks:
            for rej in rejected_feedbacks:
                insert_rejected_sql = text("""
                    INSERT INTO rejected_feedbacks (raw_payload, error_reason)
                    VALUES (:raw_payload, :error_reason)
                """)
                conn.execute(insert_rejected_sql, {
                    "raw_payload": rej["raw_payload"],
                    "error_reason": rej["error_reason"]
                })
                
        conn.commit()

    # 3. MISE À JOUR AUTOMATIQUE DU FICHIER JSON LOCAL
    update_local_json_export()

    # 4. RÉPONSE
    response_msg = (
        f"Traitement terminé. Reçus : {len(payload)} | "
        f"Succès : {len(valid_feedbacks)} | "
        f"Rejetés : {len(rejected_feedbacks)}"
    )
    logger.info(response_msg)
    
    return {
        "status": "partial_success" if rejected_feedbacks else "success",
        "message": response_msg,
        "details": {
            "inserted": len(valid_feedbacks),
            "rejected": len(rejected_feedbacks)
        }
    }