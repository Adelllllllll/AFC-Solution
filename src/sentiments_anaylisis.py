import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# GESTION DES DÉPENDANCES (Pour ne pas faire crasher Airflow)
# ---------------------------------------------------------
# On utilise un try/except pour l'import de la lourde librairie IA.
try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    logger.warning("⚠️ Module 'transformers' non détecté. Mode NLP désactivé (Normal si exécuté par Airflow).")

# ---------------------------------------------------------
# INITIALISATION GLOBALE DU MODÈLE (Chargé 1 seule fois)
# ---------------------------------------------------------
sentiment_classifier = None

if HAS_TRANSFORMERS:
    logger.info("⏳ Chargement du modèle NLP (XLM-RoBERTa)... cela peut prendre quelques secondes.")
    try:
        # Modèle multilingue (Gère très bien le FR, EN, JP, CN, etc.)
        sentiment_classifier = pipeline(
            "text-classification",
            model="cardiffnlp/twitter-xlm-roberta-base-sentiment",
            top_k=None,
            framework="pt",  # Force PyTorch
            use_fast=False,  # Désactive le tokenizer rapide pour la stabilité
            truncation=True,
            max_length=512
        )
        logger.info("✅ Modèle NLP chargé avec succès !")
    except Exception as e:
        logger.error(f"❌ Erreur lors du chargement du modèle NLP : {e}")

# ---------------------------------------------------------
# FONCTION APPELÉE PAR L'API
# ---------------------------------------------------------
def analyze_text_sentiment(text: str, neutral_to: int = 0) -> int:
    """
    Analyse un commentaire texte et retourne 1 (Positif) ou 0 (Négatif/Neutre).
    """
    # Fallback si le texte est vide, si le modèle a planté, ou si on est dans Airflow
    if not sentiment_classifier or not text or not text.strip():
        return neutral_to

    try:
        # L'IA analyse le texte
        results = sentiment_classifier(text.strip())
        
        # results[0] contient une liste de labels avec scores
        best_prediction = max(results[0], key=lambda d: d["score"])
        label = best_prediction["label"]

        # Les labels sont: 'positive', 'negative', 'neutral'
        if label == "positive":
            return 1
        elif label == "negative":
            return 0
        else:
            return neutral_to  # neutral
            
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du texte '{text[:20]}...' : {e}")
        return neutral_to