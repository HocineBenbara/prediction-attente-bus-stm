"""
=============================================================
TP - Prédiction temps d'attente autobus STM
Approche 1 : Programmation Python
=============================================================
Auteur  : TP Collecte de données
Date    : 2025
Domaine : Prédiction du temps d'attente des autobus STM
=============================================================

Processus général :
  1. Identification du besoin en données
  2. Vérification de la politique robots.txt du site STM
  3. Collecte via API (Open Data STM / GTFS-RT)
  4. Scraping aléatoire (13h00, 13h15, 13h18)
  5. Représentation des données sous forme de DataFrame
"""

import os
import requests
import pandas as pd
import time
import random
import json
from datetime import datetime
import urllib.request
import urllib.robotparser
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Récupérer la clé API depuis le fichier .env (valeur par défaut : "DEMO")
STM_API_KEY = os.getenv("STM_API_KEY", "DEMO")


# ---------------------------------------------------------
# 1. IDENTIFICATION DU BESOIN EN DONNÉES
# ---------------------------------------------------------
"""
Pour prédire le temps d'attente d'un autobus STM, on a besoin de :
  - Numéro de la ligne / route_id
  - Arrêt ciblé / stop_id
  - Heure de passage prévue (schedule)
  - Position GPS en temps réel du bus (GTFS-RT)
  - Retard observé (delay)
  - Date / heure de la collecte
  - Conditions météo (optionnel, enrichissement)
"""

BESOIN_DONNEES = [
    "route_id",       # Numéro de la ligne
    "trip_id",        # Identifiant du voyage
    "stop_id",        # Identifiant de l'arrêt
    "stop_name",      # Nom de l'arrêt
    "scheduled_time", # Heure prévue selon le schedule
    "predicted_time", # Heure prédite (GTFS-RT)
    "delay_seconds",  # Retard en secondes
    "timestamp",      # Horodatage de la collecte
    "latitude",       # Position GPS du bus
    "longitude",
    "vehicle_id",     # Identifiant du véhicule
]

print("=" * 60)
print("TP - Prédiction temps d'attente STM")
print("=" * 60)
print("\n[1] BESOIN EN DONNÉES IDENTIFIÉ :")
for col in BESOIN_DONNEES:
    print(f"    -> {col}")


# ---------------------------------------------------------
# 2. VÉRIFICATION DU ROBOTS.TXT
# ---------------------------------------------------------

def verifier_robots_txt(url_site: str, url_cible: str, user_agent: str = "*") -> dict:
    """
    Vérifie la politique de scraping du site via robots.txt.
    Retourne un dict avec les règles et l'autorisation.
    """
    rp = urllib.robotparser.RobotFileParser()
    robots_url = url_site.rstrip("/") + "/robots.txt"
    rp.set_url(robots_url)

    print(f"\n[2] VÉRIFICATION ROBOTS.TXT : {robots_url}")

    try:
        rp.read()
        autorise = rp.can_fetch(user_agent, url_cible)
        crawl_delay = rp.crawl_delay(user_agent)
        request_rate = rp.request_rate(user_agent)

        resultat = {
            "robots_url": robots_url,
            "url_cible": url_cible,
            "user_agent": user_agent,
            "scraping_autorise": autorise,
            "crawl_delay": crawl_delay,
            "request_rate": request_rate,
        }
        print(f"    [OK] Scraping autorisé : {autorise}")
        print(f"    [OK] Crawl-delay       : {crawl_delay or 'Non spécifié'} sec")
        return resultat

    except Exception as e:
        print(f"    [WARN] Impossible de lire robots.txt : {e}")
        return {"erreur": str(e), "scraping_autorise": None}


robots_info = verifier_robots_txt(
    url_site="https://www.stm.info",
    url_cible="https://www.stm.info/fr/infos/etat-du-service",
    user_agent="*",
)


# ---------------------------------------------------------
# 3. COLLECTE VIA API (GTFS-RT Open Data STM)
# ---------------------------------------------------------

# URL du flux GTFS-RT (temps réel) de la STM
GTFS_RT_URL = "https://api.stm.info/pub/od/gtfs-rt/ic/v2/tripUpdates"

# Lignes d'intérêt pour le TP (exemples : 18, 24, 55, 80, 129)
LIGNES_CIBLES = ["18", "24", "55", "80", "129"]

# Arrêts types (à ajuster selon votre zone d'étude)
ARRETS_CIBLES = {
    "18": {"stop_id": "51930", "stop_name": "Lionel-Groulx"},
    "24": {"stop_id": "52500", "stop_name": "Berri-UQAM"},
    "55": {"stop_id": "50900", "stop_name": "Saint-Laurent / Maisonneuve"},
    "80": {"stop_id": "57021", "stop_name": "Côte-des-Neiges / Van Horne"},
    "129": {"stop_id": "50401", "stop_name": "Côte-Vertu"},
}


def collecter_donnees_api_stm(api_key: str, lignes: list, arrets: dict) -> pd.DataFrame:
    """
    Collecte les données GTFS-RT via l'API officielle STM.
    Retourne un DataFrame avec les prédictions de passage.
    """
    print("\n[3] COLLECTE VIA API STM (GTFS-RT) :")
    headers = {
        "apiKey": api_key,
        "Accept": "application/json",
    }

    donnees = []

    for ligne in lignes:
        arret = arrets.get(ligne, {})
        stop_id = arret.get("stop_id", "N/A")
        stop_name = arret.get("stop_name", "N/A")

        print(f"    -> Ligne {ligne} | Arrêt {stop_name} ({stop_id})")

        try:
            response = requests.get(
                GTFS_RT_URL,
                headers=headers,
                params={"routeId": ligne},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                entites = data.get("entity", [])

                for entite in entites:
                    trip_update = entite.get("tripUpdate", {})
                    trip_id = trip_update.get("trip", {}).get("tripId", "N/A")
                    vehicle = trip_update.get("vehicle", {})
                    vehicle_id = vehicle.get("id", "N/A")

                    stop_updates = trip_update.get("stopTimeUpdate", [])
                    for su in stop_updates:
                        if su.get("stopId") == stop_id:
                            arrivee = su.get("arrival", {})
                            depart = su.get("departure", {})
                            delay = arrivee.get("delay", 0)
                            scheduled = arrivee.get("time", None)

                            donnees.append({
                                "route_id": ligne,
                                "trip_id": trip_id,
                                "stop_id": stop_id,
                                "stop_name": stop_name,
                                "scheduled_time": pd.to_datetime(scheduled, unit="s") if scheduled else None,
                                "delay_seconds": delay,
                                "predicted_wait_min": max(0, round(delay / 60, 2)),
                                "vehicle_id": vehicle_id,
                                "timestamp": datetime.now().isoformat(),
                            })
            else:
                print(f"      [WARN] HTTP {response.status_code} pour ligne {ligne}")

        except Exception as e:
            print(f"      [WARN] Erreur API ligne {ligne}: {e}")

        time.sleep(1)  # Respecter le rate-limit

    if donnees:
        df = pd.DataFrame(donnees)
        print(f"\n    [OK] {len(df)} enregistrements collectés via API")
        return df
    else:
        print("    [WARN] Aucune donnée reçue (clé API nécessaire - données simulées utilisées)")
        return generer_donnees_simulees(lignes, arrets)


# ---------------------------------------------------------
# 4. SCRAPING ALÉATOIRE (13H00 - 13H15 - 13H18)
# ---------------------------------------------------------

HEURES_SCRAPING = ["13:00", "13:15", "13:18"]  # Créneaux ciblés


def simuler_scraping_aleatoire(lignes: list, arrets: dict, heures: list) -> pd.DataFrame:
    """
    Simule un scraping aléatoire aux heures définies.
    En production : remplacer par BeautifulSoup + requests sur le site STM,
    en respectant le robots.txt vérifié précédemment.
    """
    print("\n[4] SCRAPING ALÉATOIRE AUX CRÉNEAUX CIBLÉS :")
    print(f"    Créneaux : {', '.join(heures)}")

    import re
    from bs4 import BeautifulSoup  # Utilisé si scraping HTML réel

    donnees_scraping = []
    today = datetime.now().strftime("%Y-%m-%d")

    for heure in heures:
        print(f"\n    -- Collecte à {heure} --")
        for ligne in lignes:
            arret = arrets.get(ligne, {})
            stop_name = arret.get("stop_name", "Inconnu")

            # Simulation d'une réponse scraping
            # (En production : requests.get(url) puis BeautifulSoup(response.text, "html.parser"))
            temps_attente_reel = random.randint(1, 20)
            retard = random.randint(-3, 10)

            heure_dt = datetime.strptime(f"{today} {heure}", "%Y-%m-%d %H:%M")

            record = {
                "source": "scraping",
                "heure_collecte": heure,
                "route_id": ligne,
                "stop_name": stop_name,
                "temps_attente_min": temps_attente_reel,
                "retard_min": retard,
                "timestamp": heure_dt.isoformat(),
                "methode": f"scraping_aleatoire_{heure.replace(':', 'h')}",
            }
            donnees_scraping.append(record)
            print(f"      Ligne {ligne} | {stop_name} -> {temps_attente_reel} min d'attente (retard: {retard:+d} min)")

    df_scraping = pd.DataFrame(donnees_scraping)
    print(f"\n    [OK] {len(df_scraping)} observations collectées par scraping")
    return df_scraping


# ---------------------------------------------------------
# 5. DONNÉES SIMULÉES (fallback sans clé API)
# ---------------------------------------------------------

def generer_donnees_simulees(lignes: list, arrets: dict) -> pd.DataFrame:
    """
    Génère des données réalistes simulant les flux GTFS-RT STM.
    Utilisé quand l'API n'est pas disponible (démo / TP).
    """
    print("\n    -> Génération de données simulées GTFS-RT ...")
    random.seed(42)
    donnees = []
    base_time = datetime(2025, 1, 15, 13, 0, 0)

    for ligne in lignes:
        arret = arrets.get(ligne, {})
        for i in range(8):  # 8 passages par ligne
            offset_min = i * random.randint(5, 12)
            scheduled = base_time + pd.Timedelta(minutes=offset_min)
            delay = random.randint(-120, 480)  # -2 à +8 min en secondes
            donnees.append({
                "route_id": ligne,
                "trip_id": f"trip_{ligne}_{i:03d}",
                "stop_id": arret.get("stop_id", "N/A"),
                "stop_name": arret.get("stop_name", "N/A"),
                "scheduled_time": scheduled,
                "delay_seconds": delay,
                "predicted_wait_min": max(0, round((offset_min * 60 + delay) / 60, 2)),
                "vehicle_id": f"bus_{random.randint(1000, 9999)}",
                "timestamp": datetime.now().isoformat(),
                "latitude": round(45.50 + random.uniform(-0.05, 0.05), 5),
                "longitude": round(-73.57 + random.uniform(-0.05, 0.05), 5),
            })

    return pd.DataFrame(donnees)


# ---------------------------------------------------------
# 6. ASSEMBLAGE ET REPRÉSENTATION EN DATAFRAME
# ---------------------------------------------------------

def pipeline_collecte_complet():
    """
    Pipeline complet : collecte API + scraping -> DataFrame unifié.
    """
    print("\n" + "=" * 60)
    print("DÉMARRAGE DU PIPELINE DE COLLECTE")
    print("=" * 60)

    # Collecte API (ou simulée si pas de clé)
    if STM_API_KEY == "DEMO":
        print("\n    [INFO] Pas de clé API -- Utilisation des données simulées GTFS-RT")
        df_api = generer_donnees_simulees(LIGNES_CIBLES, ARRETS_CIBLES)
    else:
        df_api = collecter_donnees_api_stm(STM_API_KEY, LIGNES_CIBLES, ARRETS_CIBLES)

    # Scraping aléatoire
    df_scraping = simuler_scraping_aleatoire(LIGNES_CIBLES, ARRETS_CIBLES, HEURES_SCRAPING)

    # -- Représentation DataFrame --
    print("\n[5] REPRÉSENTATION DES DONNÉES (DATAFRAME) :")
    print("\n-- DataFrame API / GTFS-RT --")
    print(df_api.to_string(index=False))

    print("\n-- DataFrame Scraping --")
    print(df_scraping.to_string(index=False))

    # Statistiques descriptives
    print("\n-- Statistiques - Temps d'attente (API) --")
    if "predicted_wait_min" in df_api.columns:
        stats = df_api.groupby("route_id")["predicted_wait_min"].agg(
            ["count", "mean", "min", "max", "std"]
        ).round(2)
        print(stats)

    print("\n-- Statistiques - Scraping aléatoire --")
    stats_scrap = df_scraping.groupby(["heure_collecte", "route_id"])["temps_attente_min"].mean().round(2)
    print(stats_scrap)

    # Export CSV (dans le dossier data/raw/ du projet)
    df_api.to_csv("./data/raw/donnees_api_stm.csv", index=False)
    df_scraping.to_csv("./data/raw/donnees_scraping_stm.csv", index=False)
    print("\n    [OK] Données exportées en CSV")

    return df_api, df_scraping


# ---------------------------------------------------------
# POINT D'ENTRÉE
# ---------------------------------------------------------
if __name__ == "__main__":
    df_api, df_scraping = pipeline_collecte_complet()
    print("\n" + "=" * 60)
    print("PIPELINE TERMINÉ AVEC SUCCÈS")
    print("=" * 60)