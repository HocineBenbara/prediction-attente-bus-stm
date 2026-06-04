"""
=============================================================
TP - Prédiction temps d'attente autobus STM
Approche 2 : Utilisation d'outils / Agent IA
=============================================================
Auteur  : TP Collecte de données
Date    : 2025
Description :
  Agent IA orchestrant automatiquement la collecte, le nettoyage
  et la représentation des données STM via des outils modulaires.
=============================================================

Architecture de l'agent :
  ┌─────────────────────────────────────────────────────┐
  │                     AGENT IA STM                    │
  │                                                     │
  │  Outils disponibles :                               │
  │    1. outil_verifier_robots    → Politique robots   │
  │    2. outil_appeler_api        → GTFS-RT STM        │
  │    3. outil_scraper_arret      → HTML STM (3 slots) │
  │    4. outil_nettoyer_donnees   → Normalisation      │
  │    5. outil_construire_df      → DataFrame pandas   │
  │    6. outil_visualiser         → Graphiques         │
  │    7. outil_exporter           → CSV / JSON         │
  └─────────────────────────────────────────────────────┘
"""

import requests
import pandas as pd
import json
import random
import time
from datetime import datetime
from typing import Any, Callable
import urllib.robotparser


# ─────────────────────────────────────────────────────────
# DÉFINITION DES OUTILS DE L'AGENT
# ─────────────────────────────────────────────────────────

class OutilSTM:
    """Classe de base pour tous les outils de l'agent."""

    def __init__(self, nom: str, description: str):
        self.nom = nom
        self.description = description
        self.historique_appels = []

    def executer(self, **kwargs) -> Any:
        raise NotImplementedError

    def __call__(self, **kwargs) -> Any:
        debut = datetime.now()
        resultat = self.executer(**kwargs)
        self.historique_appels.append({
            "outil": self.nom,
            "arguments": kwargs,
            "timestamp": debut.isoformat(),
            "succes": resultat is not None,
        })
        return resultat


class OutilVerifierRobots(OutilSTM):
    """Outil 1 : Vérifie la politique robots.txt d'un site."""

    def __init__(self):
        super().__init__(
            nom="verifier_robots",
            description="Vérifie si le scraping est autorisé selon robots.txt du site cible",
        )

    def executer(self, url_site: str, url_cible: str) -> dict:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(url_site.rstrip("/") + "/robots.txt")
        try:
            rp.read()
            return {
                "autorise": rp.can_fetch("*", url_cible),
                "crawl_delay": rp.crawl_delay("*"),
                "site": url_site,
            }
        except Exception as e:
            return {"autorise": None, "erreur": str(e)}


class OutilAppelerAPI(OutilSTM):
    """Outil 2 : Appelle l'API GTFS-RT de la STM."""

    def __init__(self):
        super().__init__(
            nom="appeler_api_stm",
            description="Récupère les données temps réel GTFS-RT de la STM via API REST",
        )

    def executer(self, api_key: str, ligne: str, stop_id: str) -> dict:
        if api_key == "DEMO":
            # Mode simulation pour le TP
            return self._generer_reponse_simulee(ligne, stop_id)

        headers = {"apiKey": api_key}
        url = "https://api.stm.info/pub/od/gtfs-rt/ic/v2/tripUpdates"
        try:
            r = requests.get(url, headers=headers, params={"routeId": ligne}, timeout=10)
            return r.json() if r.status_code == 200 else {"erreur": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"erreur": str(e)}

    def _generer_reponse_simulee(self, ligne: str, stop_id: str) -> dict:
        """Simulation d'une réponse API GTFS-RT."""
        passages = []
        base = datetime.now()
        for i in range(3):
            delay = random.randint(-120, 600)
            passages.append({
                "trip_id": f"trip_{ligne}_{i}",
                "stop_id": stop_id,
                "arrival_delay": delay,
                "arrival_time": int(base.timestamp()) + delay + i * 600,
                "vehicle_id": f"bus_{random.randint(1000, 9999)}",
                "latitude": round(45.50 + random.uniform(-0.05, 0.05), 5),
                "longitude": round(-73.57 + random.uniform(-0.05, 0.05), 5),
            })
        return {"route_id": ligne, "stop_id": stop_id, "passages": passages}


class OutilScraperArret(OutilSTM):
    """Outil 3 : Scrape les informations d'un arrêt STM (3 créneaux)."""

    HEURES_CIBLES = ["13:00", "13:15", "13:18"]

    def __init__(self):
        super().__init__(
            nom="scraper_arret",
            description="Scrape le temps d'attente d'un arrêt STM à des heures aléatoires prédéfinies",
        )

    def executer(self, ligne: str, stop_name: str, heures: list = None) -> list:
        heures = heures or self.HEURES_CIBLES
        resultats = []
        for h in heures:
            # Simulation scraping HTML
            time.sleep(random.uniform(0.2, 0.8))  # Délai aléatoire anti-détection
            resultats.append({
                "heure_collecte": h,
                "ligne": ligne,
                "arret": stop_name,
                "temps_attente_min": random.randint(1, 20),
                "occupation": random.choice(["faible", "moyen", "élevé"]),
                "timestamp": datetime.now().isoformat(),
            })
        return resultats


class OutilNettoyerDonnees(OutilSTM):
    """Outil 4 : Nettoie et normalise les données collectées."""

    def __init__(self):
        super().__init__(
            nom="nettoyer_donnees",
            description="Normalise, déduplique et valide les données collectées",
        )

    def executer(self, donnees: list) -> list:
        if not donnees:
            return []
        df = pd.DataFrame(donnees)
        # Supprimer les doublons
        df = df.drop_duplicates()
        # Filtrer les valeurs aberrantes
        if "temps_attente_min" in df.columns:
            df = df[df["temps_attente_min"].between(0, 60)]
        if "delay_seconds" in df.columns:
            df = df[df["delay_seconds"].between(-300, 1800)]
        return df.to_dict(orient="records")


class OutilConstruireDataFrame(OutilSTM):
    """Outil 5 : Construit le DataFrame final d'exploration."""

    def __init__(self):
        super().__init__(
            nom="construire_dataframe",
            description="Assemble toutes les données en un DataFrame pandas explorable",
        )

    def executer(self, donnees_api: list, donnees_scraping: list) -> pd.DataFrame:
        df_api = pd.DataFrame(donnees_api) if donnees_api else pd.DataFrame()
        df_scrap = pd.DataFrame(donnees_scraping) if donnees_scraping else pd.DataFrame()

        # Harmonisation des colonnes clés
        if not df_scrap.empty and "temps_attente_min" in df_scrap.columns:
            df_scrap = df_scrap.rename(columns={
                "ligne": "route_id",
                "arret": "stop_name",
                "temps_attente_min": "predicted_wait_min",
            })
            df_scrap["source"] = "scraping"

        if not df_api.empty:
            df_api["source"] = "api_gtfs_rt"

        frames = [f for f in [df_api, df_scrap] if not f.empty]
        df_final = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

        return df_final


class OutilExporter(OutilSTM):
    """Outil 6 : Exporte les données en CSV et JSON."""

    def __init__(self):
        super().__init__(
            nom="exporter_donnees",
            description="Exporte le DataFrame final en CSV et JSON",
        )

    def executer(self, df: pd.DataFrame, prefixe: str = "stm_agent") -> dict:
        if df.empty:
            return {"erreur": "DataFrame vide"}
        chemin_csv = f"/home/claude/projet_stm/{prefixe}.csv"
        chemin_json = f"/home/claude/projet_stm/{prefixe}.json"
        df.to_csv(chemin_csv, index=False)
        df.to_json(chemin_json, orient="records", force_ascii=False, indent=2)
        return {"csv": chemin_csv, "json": chemin_json, "lignes": len(df)}


# ─────────────────────────────────────────────────────────
# ORCHESTRATEUR : L'AGENT IA
# ─────────────────────────────────────────────────────────

class AgentSTM:
    """
    Agent IA orchestrant la collecte de données STM.
    
    L'agent :
      1. Planifie les étapes
      2. Choisit les outils appropriés
      3. Gère les erreurs et retry
      4. Produit un rapport d'exécution
    """

    LIGNES_CIBLES = ["18", "24", "55", "80", "129"]
    ARRETS = {
        "18": {"stop_id": "51930", "stop_name": "Lionel-Groulx"},
        "24": {"stop_id": "52500", "stop_name": "Berri-UQAM"},
        "55": {"stop_id": "50900", "stop_name": "Saint-Laurent/Maisonneuve"},
        "80": {"stop_id": "57021", "stop_name": "Côte-des-Neiges/Van Horne"},
        "129": {"stop_id": "50401", "stop_name": "Côte-Vertu"},
    }

    def __init__(self, api_key: str = "DEMO"):
        self.api_key = api_key
        self.outils = {
            "robots": OutilVerifierRobots(),
            "api": OutilAppelerAPI(),
            "scraper": OutilScraperArret(),
            "nettoyeur": OutilNettoyerDonnees(),
            "dataframe": OutilConstruireDataFrame(),
            "exporteur": OutilExporter(),
        }
        self.journal = []
        self.donnees_api = []
        self.donnees_scraping = []

    def log(self, message: str, niveau: str = "INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        entree = f"[{ts}] [{niveau}] {message}"
        self.journal.append(entree)
        print(entree)

    def executer(self) -> pd.DataFrame:
        """Lance le pipeline complet de l'agent."""
        self.log("═" * 55)
        self.log("AGENT STM DÉMARRÉ")
        self.log("═" * 55)

        # ── Étape 1 : Vérification robots.txt ──
        self.log("ÉTAPE 1 : Vérification politique robots.txt")
        robots = self.outils["robots"](
            url_site="https://www.stm.info",
            url_cible="https://www.stm.info/fr/infos/etat-du-service",
        )
        self.log(f"  → Scraping autorisé : {robots.get('autorise')}")
        self.log(f"  → Crawl-delay : {robots.get('crawl_delay', 'N/A')} sec")

        # ── Étape 2 : Collecte via API ──
        self.log("\nÉTAPE 2 : Collecte données API GTFS-RT")
        for ligne in self.LIGNES_CIBLES:
            arret = self.ARRETS.get(ligne, {})
            self.log(f"  → Requête API : Ligne {ligne} | {arret.get('stop_name')}")
            reponse = self.outils["api"](
                api_key=self.api_key,
                ligne=ligne,
                stop_id=arret.get("stop_id", ""),
            )
            for p in reponse.get("passages", []):
                self.donnees_api.append({
                    "route_id": ligne,
                    "trip_id": p.get("trip_id"),
                    "stop_id": arret.get("stop_id"),
                    "stop_name": arret.get("stop_name"),
                    "delay_seconds": p.get("arrival_delay", 0),
                    "predicted_wait_min": max(0, round(p.get("arrival_delay", 0) / 60, 2)),
                    "vehicle_id": p.get("vehicle_id"),
                    "latitude": p.get("latitude"),
                    "longitude": p.get("longitude"),
                    "timestamp": datetime.now().isoformat(),
                })
        self.log(f"  ✓ {len(self.donnees_api)} enregistrements API collectés")

        # ── Étape 3 : Scraping aux créneaux ciblés ──
        self.log("\nÉTAPE 3 : Scraping aléatoire (13h00, 13h15, 13h18)")
        for ligne in self.LIGNES_CIBLES:
            arret = self.ARRETS.get(ligne, {})
            observations = self.outils["scraper"](
                ligne=ligne,
                stop_name=arret.get("stop_name", "Inconnu"),
            )
            self.donnees_scraping.extend(observations)
        self.log(f"  ✓ {len(self.donnees_scraping)} observations scraping collectées")

        # ── Étape 4 : Nettoyage ──
        self.log("\nÉTAPE 4 : Nettoyage et normalisation des données")
        self.donnees_api = self.outils["nettoyeur"](donnees=self.donnees_api)
        self.donnees_scraping = self.outils["nettoyeur"](donnees=self.donnees_scraping)
        self.log(f"  ✓ Après nettoyage : {len(self.donnees_api)} API | {len(self.donnees_scraping)} Scraping")

        # ── Étape 5 : Construction DataFrame ──
        self.log("\nÉTAPE 5 : Construction du DataFrame unifié")
        df = self.outils["dataframe"](
            donnees_api=self.donnees_api,
            donnees_scraping=self.donnees_scraping,
        )
        self.log(f"  ✓ DataFrame final : {df.shape[0]} lignes × {df.shape[1]} colonnes")

        # ── Étape 6 : Export ──
        self.log("\nÉTAPE 6 : Export des données")
        exports = self.outils["exporteur"](df=df, prefixe="agent_stm_donnees")
        self.log(f"  ✓ CSV  : {exports.get('csv')}")
        self.log(f"  ✓ JSON : {exports.get('json')}")

        # ── Rapport ──
        self.afficher_rapport(df)
        return df

    def afficher_rapport(self, df: pd.DataFrame):
        """Affiche un rapport de synthèse."""
        self.log("\n" + "═" * 55)
        self.log("RAPPORT DE L'AGENT")
        self.log("═" * 55)
        self.log(f"  Total enregistrements     : {len(df)}")
        self.log(f"  Lignes couvertes           : {sorted(df['route_id'].unique().tolist()) if 'route_id' in df.columns else 'N/A'}")
        self.log(f"  Outils invoqués            : {sum(len(o.historique_appels) for o in self.outils.values())}")

        if "predicted_wait_min" in df.columns:
            self.log(f"\n  Temps d'attente moyen     : {df['predicted_wait_min'].mean():.1f} min")
            self.log(f"  Temps d'attente max       : {df['predicted_wait_min'].max():.1f} min")

        self.log("\n── Aperçu des données ──")
        if not df.empty:
            cols_aff = [c for c in ["route_id", "stop_name", "predicted_wait_min", "source", "heure_collecte"]
                        if c in df.columns]
            print(df[cols_aff].head(10).to_string(index=False))

        # Journal des outils
        self.log("\n── Journal des outils ──")
        for nom_outil, outil in self.outils.items():
            if outil.historique_appels:
                self.log(f"  {nom_outil:20s} : {len(outil.historique_appels)} appel(s)")

        self.log("\nAGENT STM TERMINÉ AVEC SUCCÈS ✓")


# ─────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  APPROCHE 2 : AGENT IA – COLLECTE DONNÉES STM")
    print("=" * 60)

    agent = AgentSTM(api_key="DEMO")  # Remplacer "DEMO" par votre clé API STM
    df_final = agent.executer()

    print("\n── Statistiques finales par ligne ──")
    if "predicted_wait_min" in df_final.columns and "route_id" in df_final.columns:
        print(
            df_final.groupby("route_id")["predicted_wait_min"]
            .agg(["count", "mean", "min", "max"])
            .round(2)
        )
