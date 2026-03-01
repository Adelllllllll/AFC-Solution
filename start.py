import subprocess
import sys
import time
import threading
import json

# Services à surveiller au démarrage
CRITICAL_SERVICES = ["ndai_fastapi", "afc-solution-airflow-webserver-1"]

def is_container_healthy(container_name):
    """Vérifie l'état de santé via Docker Inspect."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{json .State.Health.Status}}", container_name],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip().replace('"', '') == "healthy"
    except:
        pass
    return False

def print_loading_messages(stop_event):
    """Affiche tes messages originaux."""
    messages = [
        "⏳ Lancement de l'infrastructure en cours...(cela prendre plusieurs minutes, merci de patienter)",
        "⏳ Pas de panique, l'application n'a pas planté ! Le chargement est tout à fait normal...",
        "⏳ On installe l'Intelligence Artificielle dans la RAM (c'est lourd un cerveau numérique)...",
        "⏳ Apache Airflow prend son café pour se réveiller (il lui faut une petite minute)...",
        "⏳ Toujours là ! Ne quittez pas, on fait chauffer les serveurs...",
    ]
    idx = 0
    while not stop_event.is_set():
        print(messages[idx % len(messages)], flush=True)
        idx += 1
        for _ in range(60):
            if stop_event.is_set(): break
            time.sleep(1)

def wait_for_api_completion():
    """Écoute les logs de l'API et s'arrête quand le traitement est fini."""
    print("En attente du traitement IA... (Je surveille les logs de l'API)", flush=True)
    
    # On lance 'docker logs -f' (follow) pour lire le flux en direct
    process = subprocess.Popen(
        ["docker", "logs", "-f", "ndai_fastapi"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8"
    )

    try:
        for line in process.stdout:
            # On cherche le message spécifique défini dans api_feedback.py
            if "Traitement terminé" in line:
                print(f"\nLog détecté : {line.strip()}")
                process.terminate()
                return True
    except Exception as e:
        print(f"Erreur d'écoute : {e}")
        process.terminate()
    return False

def main():
    print("\n ÉTAPE 1 : Lancement de l'infrastructure...\n", flush=True)
    subprocess.run(["docker-compose", "up", "-d"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Animation de démarrage
    stop_event = threading.Event()
    loader_thread = threading.Thread(target=print_loading_messages, args=(stop_event,))
    loader_thread.start()
    
    while not all([is_container_healthy(s) for s in CRITICAL_SERVICES]):
        time.sleep(5)

    stop_event.set()
    loader_thread.join()
        
    print("\n[OK] L'infrastructure est prête.", flush=True)
    print("\n ÉTAPE 2 : Ingestion des données")
    print(" Allez dans votre autre terminal et lancez 'python src\\__main__.py PUSH 1000' (ou 100).", flush=True)
    
    # On lance l'écouteur de logs
    if wait_for_api_completion():
        print("\n=======================================================")
        print("[SUCCÈS] L'ANALYSE IA EST TERMINÉE !")
        print("=======================================================\n", flush=True)
        
        print("--- 1. ORCHESTRATION ---")
        print("Lancez votre DAG Airflow ici : http://localhost:8081\n")

        print("--- 2. DASHBOARD FINAL ---")
        print("Une fois le DAG Airflow terminé (vert), tapez :")
        print("docker-compose up -d streamlit")
        print("Lien : http://localhost:8501\n")

if __name__ == "__main__":
    main()