# 1. On part d'un mini-ordinateur Linux avec Python 3.10 pré-installé
FROM python:3.10-slim

# 2. On définit le dossier de travail à l'intérieur du conteneur
WORKDIR /app

# 3. On copie le fichier des dépendances depuis ton PC vers le conteneur
COPY requirements.txt .

# 4. On installe les librairies
RUN pip install --no-cache-dir -r requirements.txt

# 5. On copie le code source Streamlit dans le conteneur
COPY dashboard.py .

# 6. On indique que ce conteneur communiquera sur le port 8501
EXPOSE 8501

# 7. La commande exécutée au démarrage du conteneur
CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]