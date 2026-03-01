# 🍗 N.D.A.I - Armoric Fried Chicken (AFC) : Executive Data Platform

Bienvenue dans le guide de déploiement de la plateforme Data & IA d'Armoric Fried Chicken. Ce projet met en place une architecture ELT moderne, couplée à une API d'Intelligence Artificielle en temps réel (NLP) pour analyser les ventes et la satisfaction client.

## Prérequis
Avant de commencer, assurez-vous d'avoir installé sur votre machine :
- Docker et Docker Compose (Docker Desktop recommandé sous Windows/Mac)
- Python 3.10+
- Git

---

## Étape 1 : Installation et Configuration

**1. Cloner le dépôt GitHub :**
Ouvrez un terminal et tapez :
`git clone https://github.com/Adelllllllll/AFC-Solution
`cd AFC-Solution`

**2. Configuration du générateur de données (config.ini) :**
Naviguez dans le dossier de votre générateur de données (api_pusher) et ouvrez le fichier `config.ini`. 
Vous devez modifier deux sections importantes : l'URL de l'API locale et les chemins absolus vers vos fichiers CSV bruts situés dans le dossier `AFC-Solution/data/raw/`.

Modifiez le fichier pour qu'il ressemble à ceci (en remplaçant `C:/Chemin/Vers/Le/Projet/` par votre vrai chemin absolu) :

[API]
endpoint_url = http://localhost:8080/afc/api
method = POST
timeout_seconds = 10

[CSV]
sales_file_path = C:/Chemin/Vers/Le/Projet/AFC-Solution/data/raw/
sales_file_name = sales_data.csv
campaign_product_file_path = C:/Chemin/Vers/Le/Projet/AFC-Solution/data/raw/
campaign_product_file_name = campaign_product.csv

*(Note : Assurez-vous de bien laisser le slash `/` à la fin des chemins de dossiers).*

---

## Étape 2 : Démarrage de l'Infrastructure

L'ensemble de l'infrastructure (Base de données, Data Lake, Orchestrateur, API IA) est conteneurisé.

**1.** Ouvrez un terminal dans le dossier racine `AFC-Solution`.

**2.** Lancez le script de démarrage intelligent en tapant :
`python start.py`

**3.** Patientez. Le script va télécharger les images Docker, initialiser Apache Airflow et charger le modèle IA multilingue (XLM-RoBERTa) dans la mémoire RAM.
> *Ne quittez pas le terminal tant que le message vert "✅ [SUCCES] L'INFRASTRUCTURE EST UP ET HEALTHY !" n'est pas apparu, celà peut prendre 10min.*

---

## Étape 3 : Ingestion des Données (API & S3)

Une fois l'infrastructure prête, nous allons simuler l'arrivée de données métiers via notre script PUSHER.

**1.** Ouvrez un nouveau terminal et allez dans le dossier du pusher :
`cd ../api_pusher-main`

**2.** Envoyez les données de ventes brutes vers le Data Lake (LocalStack S3) :
`python src\__main__.py CSV 1000`

**3.** Envoyez les retours clients (Streaming) à l'API IA :
`python src\__main__.py PUSH 1000`

*Note : L'API reçoit les données, analyse le sentiment des commentaires multilingues à la volée grâce au modèle NLP pré-chargé, et les insère dans PostgreSQL, l'enrichissement par IA peut prendre quelques minutes*

---

## Étape 4 : Orchestration (Apache Airflow)

Maintenant que les données brutes sont ingérées, nous devons les nettoyer et les modéliser.

**1.** Ouvrez votre navigateur et allez sur l'interface Airflow : http://localhost:8081
**2.** Connectez-vous avec les identifiants par défaut (ID : `airflow`, Mot de passe : `airflow`).
**3.** Activez (Unpause) votre DAG principal et lancez-le manuellement en cliquant sur le bouton "Play" (Trigger DAG).

*Ce DAG va se connecter à S3, nettoyer les données, les charger dans PostgreSQL et déclencher la création de nos Vues SQL matérialisées.*

---

## Étape 5 : L'Executive Dashboard (Streamlit)

Une fois les données traitées, il est temps de les visualiser.

**1.** Retournez dans le terminal du projet `AFC-Solution`.

**2.** Lancez le conteneur contenant l'interface analytique avec la commande :
`docker-compose up -d streamlit`

**3.** Ouvrez votre navigateur sur : http://localhost:8501

---

## Étape 6 : Nettoyage et Arrêt

Pour éteindre proprement l'infrastructure, libérer les ports réseau et vider la RAM de votre machine, tapez :
`docker-compose down`

*(Le modèle d'IA de 500 Mo restera en cache sur votre machine locale pour accélérer considérablement les prochains lancements).*