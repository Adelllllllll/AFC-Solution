# N.D.A.I - Armoric Fried Chicken (AFC) : Executive Data Platform

Ce guide detaille le deploiement de la plateforme Data et IA d'Armoric Fried Chicken. Le projet repose sur une architecture ELT complete, integree a une API d'Intelligence Artificielle (NLP) traitant les flux de donnees en temps reel.

## 1. Prerequis
Assurez-vous d'avoir installe les outils suivants :
- Docker et Docker Compose (Docker Desktop recommande)
- Python 3.10+
- Git

---

## 2. Installation et Configuration

1. Clonage du depot :
Ouvrez un terminal et tapez :
git clone https://github.com/Adelllllllll/AFC-Solution
cd AFC-Solution

2. Configuration du pusher (config.ini) :
Naviguez dans le dossier de votre generateur de donnees (api_pusher) et configurez le fichier config.ini. L'URL doit pointer vers le port 8080. Utilisez des chemins absolus pour les fichiers CSV.

Exemple de configuration :
[API]
endpoint_url = http://localhost:8080/afc/api
method = POST
timeout_seconds = 10

[CSV]
sales_file_path = C:/Chemin/Vers/Le/Projet/AFC-Solution/data/raw/
sales_file_name = sales_data.csv
campaign_product_file_path = C:/Chemin/Vers/Le/Projet/AFC-Solution/data/raw/
campaign_product_file_name = campaign_product.csv

*Note : Verifiez bien la presence du slash final dans les chemins de dossiers.*

---

## 3. Demarrage de l'Infrastructure

L'infrastructure utilise un reseau nomme isole (afc_network) pour garantir la stabilite des communications entre les conteneurs.

1. Lancement automatique :
Executez le script de demarrage depuis la racine du projet :
python start.py

2. Chargement de l'IA :
Le script attend que l'API FastAPI soit operationnelle et que le modele XLM-RoBERTa soit charge en memoire. Un volume persistant (hf_cache) est utilise pour stocker le modele et eviter les telechargements repetitifs.

---

## 4. Ingestion et Analyse IA

Une fois que le script indique que l'infrastructure est prete, procedez a l'envoi des donnees.

1. Terminal Ingestion :
cd ../api_pusher-main

2. Envoi des donnees :
- Ventes (vers S3) : python src\__main__.py CSV 1000
- Feedbacks (vers API IA) : python src\__main__.py PUSH 1000

3. Surveillance :
Le script start.py utilise un encodage UTF-8 pour lire les flux de logs de l'API sans erreur. Il vous informera automatiquement des que le message "Traitement termine" est detecte dans les logs.

---

## 5. Orchestration et Vues Analytiques

Le Dashboard depend de la creation de vues SQL specifiques effectuee par l'orchestrateur.

1. Acceder a Airflow : http://localhost:8081 (Identifiants : airflow / airflow).
2. Execution : Activez et declenchez le DAG "sales_daily_ingest".
3. Transformation : Ce DAG nettoie les donnees brutes de S3 et genere les vues SQL view_global_kpi, view_sales_by_country et view_campaign_feedback_stats dans PostgreSQL.

---

## 6. Dashboard Streamlit

Le Dashboard integre une securite qui empeche le plantage en cas d'absence de donnees.

1. Lancement :
docker-compose up -d streamlit

2. Consultation : http://localhost:8501

3. Gestion des erreurs :
Si les vues SQL ne sont pas encore creees par Airflow, le dashboard affichera un message d'instruction au lieu de bloquer sur un chargement infini. Il suffit de relancer le conteneur streamlit puis rafraichir la page une fois le DAG Airflow termine.

---

## 7. Arret du Projet

Pour liberer les ressources et couper proprement les reseaux Docker :
docker-compose down

*Les donnees traitees et le cache du modele d'IA sont conserves dans des volumes Docker nommes pour une reutilisation rapide.*