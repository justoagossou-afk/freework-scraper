# 🕷️ Freework Scraper

Pipeline automatisé de scraping de missions freelance depuis Freework.com,
orchestré avec Apache Airflow et stocké dans PostgreSQL.

## 📋 Description

Ce projet scrape automatiquement les missions freelance disponibles sur Freework,
les stocke dans une base de données PostgreSQL et orchestre le tout avec Apache Airflow.
Le pipeline tourne tous les jours à 9h00.

## 🛠️ Stack technique

| Outil | Version | Rôle |
|-------|---------|------|
| Python | 3.14 | Scraping et traitement des données |
| PostgreSQL | 18 | Stockage des missions |
| Apache Airflow | 2.x | Orchestration du pipeline |
| Docker | 29.x | Containerisation |
| SQLAlchemy | latest | ORM pour PostgreSQL |
| Loguru | latest | Logging |

## 📁 Structure du projet

freework-scraper/
├── dags/
│   └── freework_dag.py        # DAG Airflow principal
├── scraper/
│   ├── main.py                # Point d'entrée du scraper
│   └── database.py            # Connexion et opérations PostgreSQL
├── Dockerfile                 # Image Docker du scraper
├── Dockerfile.airflow         # Image Docker Airflow
├── docker-compose.yaml        # Services principaux
├── docker-compose.airflow.yaml # Services Airflow
├── requirements.txt           # Dépendances Python
└── .env.example               # Variables d'environnement exemple

## ⚙️ Installation

### Prérequis
- Docker et Docker Compose
- Git
 Lancer les services
```bash
docker compose up -d
```

## 🔄 Pipeline Airflow

Le DAG `freework_scraper` contient 3 tâches :

1. `creer_table` — Crée la table PostgreSQL si elle n'existe pas
2. `scraper_freework` — Scrape les missions depuis Freework
3. `verifier_donnees` — Vérifie et valide les données insérées

**Planification :** Tous les jours à 9h00 (`0 8 * * *`)

## 🔐 Variables d'environnement

```env
SCRAPER_DB_USER=postgres
SCRAPER_DB_PASSWORD=your_password
SCRAPER_DB_NAME=freework
SCRAPER_DB_HOST=postgres
SCRAPER_DB_PORT=5432
```

## 👤 Auteur

**Justo Agossou** — Data Engineer
- GitHub: [@justoagossou-afk](https://github.com/justoagossou-afk)
  
