# Prediction du temps d'attente des autobus STM

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![STM Open Data](https://img.shields.io/badge/Data-STM%20Open%20Data-orange.svg)](https://www.stm.info/fr/a-propos/developpeurs)

Projet de collecte, nettoyage et analyse des donnees en temps reel des autobus de la Societe de transport de Montreal (STM) afin de predire les temps d'attente aux arrets.

Le projet compare deux architectures de collecte :
- **Approche 1** : Pipeline Python classique (fonctions procedurales).
- **Approche 2** : Orchestration par un **Agent IA modulaire** base sur des outils reutilisables.

---

## Objectifs

- Collecter les donnees de passage en temps reel via l'**API GTFS-RT** officielle de la STM.
- Verifier la conformite legale via le fichier `robots.txt`.
- Enrichir les donnees par du **scraping web** sur des creneaux definis (13h00, 13h15, 13h18).
- Nettoyer, normaliser et exporter les donnees (CSV / JSON).
- Fournir une base solide pour l'entrainement de modeles de Machine Learning (prediction de retard).

---

## Architecture du projet

```text
stm-bus-eta-prediction/
|
|-- .env.example                 # Modele de fichier d'environnement (sans vraie cle)
|-- .gitignore                   # Regles d'exclusion Git (protege la cle API)
|-- README.md                    # Documentation principale
|-- requirements.txt             # Dependances Python
|
|-- data/                        # Donnees brutes et traitees (non versionnees)
|   |-- raw/
|   |   +-- .gitkeep
|   +-- processed/
|       +-- .gitkeep
|
|-- notebooks/                   # Analyse exploratoire (EDA) et visualisations
|   +-- 01_exploration_donnees_stm.ipynb
|
|-- src/                         # Code source principal
|   |-- __init__.py
|   |-- workflow_processus.py    # Workflow BPMN-like de la collecte
|   |-- approche1_collecte.py    # Pipeline de collecte classique
|   |-- approche2_agent.py       # Orchestration par Agent IA (outils modulaires)
|   +-- utils/
|       |-- __init__.py
|       +-- config.py            # Gestion securisee des variables d'environnement
|
+-- tests/                       # Tests unitaires
    |-- __init__.py
    +-- test_agent_stm.py