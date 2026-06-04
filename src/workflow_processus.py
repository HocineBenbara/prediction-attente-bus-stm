"""
=============================================================
NOTATION DU PROCESSUS – Workflow BPMN-like
Prédiction temps d'attente STM
=============================================================

┌──────────────────────────────────────────────────────────────────────────────┐
│                    PROCESSUS COLLECTE DONNÉES STM                            │
│                         (Notation BPMN simplifiée)                           │
└──────────────────────────────────────────────────────────────────────────────┘

  [DÉBUT] ─────────────────────────────────────────────────────────────────────
     │
     ▼
  [Tâche 1] Définir le domaine & objectif
     │  → Domaine : Prédiction temps d'attente autobus STM
     │  → Besoin  : Données temps réel + historiques
     │
     ▼
  [Tâche 2] Identifier le besoin en données
     │  → Variables cibles : delay_seconds, predicted_wait_min
     │  → Identifiants    : route_id, stop_id, trip_id
     │  → Enrichissement  : GPS (lat/lon), vehicle_id, météo
     │
     ▼
  [Tâche 3] Vérifier politique robots.txt du site STM
     │  URL : https://www.stm.info/robots.txt
     │  → OUI : scraping autorisé → continuer
     │  → NON : utiliser API officielle uniquement
     │
     ▼
  [Gateway] : Méthode de collecte disponible ?
     ├─── [API disponible] ──────────────────────────────────────────────────►
     │         ▼
     │    [Tâche 4a] Appel API GTFS-RT STM
     │         │  → Endpoint : api.stm.info/pub/od/gtfs-rt/ic/v2/tripUpdates
     │         │  → Paramètres : routeId, stopId
     │         │  → Format réponse : JSON / protobuf
     │         │
     │         ▼
     │    [Tâche 4b] Parser la réponse JSON
     │         │  → Extraire : trip_id, delay, arrival_time, vehicle_id
     │         │
     └─── [Scraping web] ────────────────────────────────────────────────────►
               ▼
          [Tâche 4c] Scraping aléatoire – 3 créneaux
               │  → Heure 1 : 13h00
               │  → Heure 2 : 13h15
               │  → Heure 3 : 13h18
               │  → Module  : requests + BeautifulSoup
               │  → Respect : crawl-delay robots.txt
               │
     ▼
  [Tâche 5] Nettoyage & validation des données
     │  → Suppression doublons
     │  → Filtrage valeurs aberrantes (attente > 0 min et < 60 min)
     │  → Normalisation des types (datetime, float)
     │
     ▼
  [Tâche 6] Représentation en DataFrame (pandas)
     │  → Colonnes : route_id | stop_name | predicted_wait_min | delay_seconds
     │              timestamp | vehicle_id | latitude | longitude | source
     │
     ▼
  [Tâche 7] Analyse exploratoire
     │  → Statistiques descriptives par ligne
     │  → Visualisation : histogramme des temps d'attente
     │  → Corrélations : retard vs heure, ligne, arrêt
     │
     ▼
  [Tâche 8] Export des données
     │  → Format CSV  : donnees_stm.csv
     │  → Format JSON : donnees_stm.json
     │
     ▼
  [FIN] ────────────────────────────────────────────────────────────────────────


=============================================================
DÉCISIONS CLÉS DU PROCESSUS
=============================================================

Decision 1 – robots.txt
  → Si scraping interdit : utiliser exclusivement l'API GTFS-RT
  → Si scraping autorisé : combiner API + scraping pour enrichissement

Decision 2 – Disponibilité API
  → Clé API valide  : données temps réel officielles
  → Pas de clé API  : données simulées / historiques GTFS statique

Decision 3 – Qualité des données
  → Si >20% de valeurs manquantes : relancer la collecte
  → Si données aberrantes détectées : appliquer filtres IQR


=============================================================
MAPPING APPROCHE 1 vs APPROCHE 2
=============================================================

  Étape                     | Approche 1 (Python)      | Approche 2 (Agent IA)
  ──────────────────────────|──────────────────────────|──────────────────────────
  Vérif. robots.txt         | Fonction directe         | OutilVerifierRobots
  Collecte API              | Fonction collecter_api() | OutilAppelerAPI
  Scraping                  | simuler_scraping()       | OutilScraperArret
  Nettoyage                 | Inline dans pipeline     | OutilNettoyerDonnees
  Construction DataFrame    | pd.DataFrame() direct    | OutilConstruireDataFrame
  Export                    | df.to_csv()              | OutilExporter
  Orchestration             | pipeline_collecte()      | AgentSTM.executer()
  Réutilisabilité           | Moyenne                  | Élevée (plug & play)
  Extensibilité             | Refactoring requis       | Ajout d'outil simple
"""
