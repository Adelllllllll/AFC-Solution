import os
import json
import logging
import random
from typing import List, Dict, Any
from fastapi import FastAPI
from pydantic import BaseModel, ValidationError
from sqlalchemy import create_engine, text

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
    description="API temps réel avec tolérance aux pannes (DLQ). Analyse NLP simulée pour le moment."
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

def set_sentiments(text_to_analyze: str) -> int:
    """
    Fonction 'Bouchon' (Stub).
    Simule l'étape de NLP en attribuant aléatoirement 0 ou 1.
    Sera remplacée par l'implémentation NLTK plus tard.
    """
    # On simule un calcul arbitraire
    return random.choice([0, 1])

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
            
    # 2. ENRICHISSEMENT (SIMULÉ) ET INSERTION
    engine = get_db_engine()
    
    with engine.connect() as conn:
        # A. Insertion des succès
        if valid_feedbacks:
            for fb in valid_feedbacks:
                # Appel de notre fonction bouchon
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

    # 3. RÉPONSE
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